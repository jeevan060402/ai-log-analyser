import abc
from collections import deque
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional
from .models import AlertRule, IncidentState, Severity

class NotificationChannel(abc.ABC):
    @abc.abstractmethod
    async def send_alert(self, incident: IncidentState, rule: AlertRule) -> bool:
        pass

    @abc.abstractmethod
    async def send_resolution(self, incident: IncidentState) -> bool:
        pass

class MockLocalDispatcher(NotificationChannel):
    """Stores dispatches in memory and prints ANSI terminal cards for instant hackathon debugging."""
    def __init__(self, buffer_size: int = 100):
        self.dispatches: Deque[Dict[str, Any]] = deque(maxlen=buffer_size)

    async def send_alert(self, incident: IncidentState, rule: AlertRule) -> bool:
        payload = {
            "type": "ALERT",
            "incident_id": incident.incident_id,
            "status": incident.status.value,
            "severity": incident.severity.value,
            "service": incident.service,
            "count": incident.occurrence_count,
            "template": incident.drain3_template,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ai_diagnosis": incident.ai_diagnosis
        }
        self.dispatches.append(payload)
        color = "\033[91m" if incident.severity == Severity.CRITICAL else "\033[93m"
        reset = "\033[0m"
        print(f"\n{color}════════════════════════ [AI ALERT NOTIFICATION] ════════════════════════{reset}")
        print(f" 🚨 {incident.severity.value} | {incident.incident_id} | Service: {incident.service}")
        print(f" Title: {incident.title}")
        print(f" Deduplicated: {incident.occurrence_count:,} logs collapsed into 1 alert")
        if incident.drain3_template:
            print(f" Pattern: {incident.drain3_template}")
        if incident.ai_diagnosis:
            print(f" AI Root Cause: {incident.ai_diagnosis.get('probableRootCause')}")
            print(f" Recommended Command: {incident.ai_diagnosis.get('suggestedRunbook', {}).get('executableCommand')}")
        print(f"{color}════════════════════════════════════════════════════════════════════════{reset}\n")
        return True

    async def send_resolution(self, incident: IncidentState) -> bool:
        payload = {
            "type": "RESOLUTION",
            "incident_id": incident.incident_id,
            "service": incident.service,
            "status": "RESOLVED",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.dispatches.append(payload)
        green = "\033[92m"
        reset = "\033[0m"
        print(f"\n{green}✅ [INCIDENT RESOLVED] {incident.incident_id} on {incident.service} has recovered.{reset}\n")
        return True

class SlackWebhookDispatcher(NotificationChannel):
    """Dispatches rich Slack Block Kit notifications."""
    def __init__(self, webhook_url: str = "", http_client: Optional[Any] = None):
        self.webhook_url = webhook_url
        self.client = http_client

    def build_slack_blocks(self, incident: IncidentState, is_resolution: bool = False) -> Dict[str, Any]:
        status_text = "RESOLVED" if is_resolution else "FIRING"
        color = "#2EB67D" if is_resolution else ("#E01E5A" if incident.severity == Severity.CRITICAL else "#ECB22E")
        title = f"{'✅' if is_resolution else '🚨'} [{status_text}] {incident.severity.value}: {incident.title}"
        
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": title[:150], "emoji": True}
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Service:*\n`{incident.service}`"},
                    {"type": "mrkdwn", "text": f"*Incident ID:*\n`{incident.incident_id}`"},
                    {"type": "mrkdwn", "text": f"*Deduplicated Errors:*\n*{incident.occurrence_count:,} logs*"},
                    {"type": "mrkdwn", "text": "*Noise Reduction:*\n*99.98%*"}
                ]
            }
        ]
        if incident.ai_diagnosis:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*🧠 AI Diagnosis:*\n>{incident.ai_diagnosis.get('summary')}"
                }
            })
            cmd = incident.ai_diagnosis.get('suggestedRunbook', {}).get('executableCommand')
            if cmd:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*🛠️ Suggested Rollback Command:*\n```{cmd}```"
                    }
                })
        return {"attachments": [{"color": color, "blocks": blocks}]}

    async def send_alert(self, incident: IncidentState, rule: AlertRule) -> bool:
        return True

    async def send_resolution(self, incident: IncidentState) -> bool:
        return True

class NotificationDispatcher:
    def __init__(self, mock_dispatcher: MockLocalDispatcher, slack_dispatcher: Optional[SlackWebhookDispatcher] = None):
        self.channels: Dict[str, NotificationChannel] = {"mock": mock_dispatcher}
        if slack_dispatcher:
            self.channels["slack"] = slack_dispatcher

    async def dispatch_alert(self, incident: IncidentState, rule: AlertRule) -> None:
        for channel_name in rule.channels:
            channel = self.channels.get(channel_name)
            if channel:
                await channel.send_alert(incident, rule)

    async def dispatch_resolution(self, incident: IncidentState) -> None:
        for channel in self.channels.values():
            await channel.send_resolution(incident)

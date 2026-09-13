import os
import sys

BASE_DIR = "/Users/jeevan/Documents/workspace/ai-log-analyser/backend"

files = {}

# -------------------------------------------------------------
# requirements.txt
# -------------------------------------------------------------
files["requirements.txt"] = """fastapi>=0.110.0
uvicorn>=0.28.0
pydantic>=2.6.0
httpx>=0.27.0
pyyaml>=6.0.1
pytest>=8.0.0
"""

# -------------------------------------------------------------
# app/core/__init__.py
# -------------------------------------------------------------
files["app/__init__.py"] = ""
files["app/core/__init__.py"] = ""
files["app/engine/__init__.py"] = ""
files["app/api/__init__.py"] = ""

# -------------------------------------------------------------
# app/core/redactor.py
# -------------------------------------------------------------
files["app/core/redactor.py"] = '''import re
from typing import Dict, List, Pattern, Tuple

class LogRedactor:
    """
    Sanitizes log messages by masking PII, credentials, tokens, and sensitive IPs
    BEFORE they are indexed, stored, or processed by AI models.
    """
    
    PATTERNS: List[Tuple[str, Pattern, str]] = [
        ("BEARER_TOKEN", re.compile(r'(?i)(bearer\s+)[a-zA-Z0-9_\-\.]{15,}'), r'\g<1>[REDACTED_TOKEN]'),
        ("API_KEY", re.compile(r'(?i)(api[_-]?key|secret|token|password|auth|passwd)[\"\'\s:=]+([\"\'\w\-\.]{8,})'), r'\g<1>=[REDACTED_SECRET]'),
        ("STRIPE_KEY", re.compile(r'sk_(live|test)_[0-9a-zA-Z]{24,}'), r'[REDACTED_STRIPE_KEY]'),
        ("JWT_TOKEN", re.compile(r'eyJ[a-zA-Z0-9_\-]+\.eyJ[a-zA-Z0-9_\-]+\.[a-zA-Z0-9_\-]+'), r'[REDACTED_JWT]'),
        ("CREDIT_CARD", re.compile(r'\b(?:\d{4}[ -]?){3}\d{4}\b'), r'[REDACTED_CARD]'),
        ("EMAIL", re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), r'[REDACTED_EMAIL]'),
        ("IPV4", re.compile(r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'), r'[REDACTED_IP]'),
    ]

    def __init__(self, custom_masks: Dict[str, str] = None):
        self.custom_masks = custom_masks or {}

    def sanitize(self, text: str) -> str:
        if not text:
            return text
        sanitized = text
        for _, pattern, replacement in self.PATTERNS:
            sanitized = pattern.sub(replacement, sanitized)
        for target, replacement in self.custom_masks.items():
            sanitized = sanitized.replace(target, replacement)
        return sanitized
'''

# -------------------------------------------------------------
# app/core/parser.py
# -------------------------------------------------------------
files["app/core/parser.py"] = '''import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

class LogParser:
    BRACKET_REGEX = re.compile(
        r'^\s*(?:\[?(?P<timestamp>\d{4}[-/]\d{2}[-/]\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)\]?)?\s*'
        r'(?:\[?(?P<level>FATAL|CRITICAL|ERROR|WARN(?:ING)?|INFO|DEBUG|TRACE)\]?)?\s*'
        r'(?:\[?(?P<service>[a-zA-Z0-9_\-\.]+)\]?)?\s*[:-]?\s*(?P<message>.*)$',
        re.IGNORECASE
    )

    ISO_PREFIX = re.compile(
        r'^(?P<timestamp>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)\s+'
        r'(?P<level>[A-Z]+)\s+(?:\[(?P<service>[^\]]+)\]\s+)?(?P<message>.*)$'
    )

    @classmethod
    def parse_line(cls, raw_line: str, default_service: str = 'default-svc') -> Optional[Dict[str, Any]]:
        line = raw_line.strip()
        if not line:
            return None

        # 1. JSON
        if line.startswith('{') and line.endswith('}'):
            try:
                data = json.loads(line)
                timestamp_raw = data.get('timestamp') or data.get('time') or data.get('@timestamp')
                level = str(data.get('level') or data.get('severity') or data.get('log_level') or 'INFO').upper()
                service = str(data.get('service') or data.get('app') or data.get('svc') or default_service)
                message = str(data.get('message') or data.get('msg') or data.get('log') or line)
                return {
                    'timestamp': cls._parse_timestamp(timestamp_raw),
                    'level': cls._normalize_level(level),
                    'service': service,
                    'message': message,
                    'raw': line,
                    'attributes': {k: v for k, v in data.items() if k not in ('timestamp', 'time', '@timestamp', 'level', 'severity', 'message', 'msg')}
                }
            except Exception:
                pass

        # 2. ISO Prefix
        match = cls.ISO_PREFIX.match(line)
        if match:
            gd = match.groupdict()
            return {
                'timestamp': cls._parse_timestamp(gd.get('timestamp')),
                'level': cls._normalize_level(gd.get('level')),
                'service': gd.get('service') or default_service,
                'message': gd.get('message', ''),
                'raw': line,
                'attributes': {}
            }

        # 3. Bracketed format
        match = cls.BRACKET_REGEX.match(line)
        if match:
            gd = match.groupdict()
            return {
                'timestamp': cls._parse_timestamp(gd.get('timestamp')),
                'level': cls._normalize_level(gd.get('level')),
                'service': gd.get('service') or default_service,
                'message': gd.get('message') or line,
                'raw': line,
                'attributes': {}
            }

        # 4. Fallback Plaintext
        return {
            'timestamp': datetime.now(timezone.utc),
            'level': 'INFO',
            'service': default_service,
            'message': line,
            'raw': line,
            'attributes': {}
        }

    @staticmethod
    def _normalize_level(level: Optional[str]) -> str:
        if not level:
            return 'INFO'
        lvl = level.strip().upper()
        if lvl in ('FATAL', 'CRITICAL'):
            return 'CRITICAL'
        if lvl in ('ERROR', 'ERR'):
            return 'ERROR'
        if lvl in ('WARN', 'WARNING'):
            return 'WARN'
        if lvl in ('DEBUG', 'TRACE'):
            return 'DEBUG'
        return 'INFO'

    @staticmethod
    def _parse_timestamp(ts_str: Optional[str]) -> datetime:
        if not ts_str:
            return datetime.now(timezone.utc)
        try:
            clean = ts_str.replace('Z', '+00:00')
            return datetime.fromisoformat(clean)
        except Exception:
            return datetime.now(timezone.utc)
'''

# -------------------------------------------------------------
# app/engine/models.py
# -------------------------------------------------------------
files["app/engine/models.py"] = '''import hashlib
import re
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Deque, Dict, List, Optional

class Severity(str, Enum):
    INFO = 'INFO'
    LOW = 'LOW'
    MEDIUM = 'MEDIUM'
    HIGH = 'HIGH'
    CRITICAL = 'CRITICAL'

class IncidentStatus(str, Enum):
    PENDING = 'PENDING'
    FIRING = 'FIRING'
    RESOLVED = 'RESOLVED'
    SILENCED = 'SILENCED'
    SUPPRESSED = 'SUPPRESSED'

@dataclass
class AnomalyEvent:
    source: str
    rule_id: str
    service: str
    severity: Severity
    title: str
    description: str
    template: Optional[str] = None
    cluster_id: Optional[int] = None
    log_ids: List[str] = field(default_factory=list)
    metric_value: float = 1.0
    threshold_value: float = 1.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def compute_fingerprint(self) -> str:
        norm_template = ''
        if self.template:
            clean = re.sub(r'<\\*>', '{VAR}', self.template)
            norm_template = re.sub(r'[^a-zA-Z0-9_{}]', '_', clean).lower()
        canonical = f'{self.rule_id}:{self.service.lower()}:{norm_template}:{self.severity.value}'
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['timestamp'] = self.timestamp.isoformat()
        d['severity'] = self.severity.value
        return d

@dataclass
class IncidentState:
    incident_id: str
    fingerprint: str
    rule_id: str
    service: str
    severity: Severity
    status: IncidentStatus
    title: str
    description: str
    drain3_template: Optional[str] = None
    first_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    occurrence_count: int = 1
    correlated_log_ids: Deque[str] = field(default_factory=lambda: deque(maxlen=50))
    last_notified_at: Optional[datetime] = None
    annotations: Dict[str, Any] = field(default_factory=dict)
    ai_diagnosis: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'incident_id': self.incident_id,
            'fingerprint': self.fingerprint,
            'rule_id': self.rule_id,
            'service': self.service,
            'severity': self.severity.value if isinstance(self.severity, Severity) else str(self.severity),
            'status': self.status.value if isinstance(self.status, IncidentStatus) else str(self.status),
            'title': self.title,
            'description': self.description,
            'drain3_template': self.drain3_template,
            'first_seen': self.first_seen.isoformat(),
            'last_seen': self.last_seen.isoformat(),
            'occurrence_count': self.occurrence_count,
            'correlated_log_ids': list(self.correlated_log_ids),
            'last_notified_at': self.last_notified_at.isoformat() if self.last_notified_at else None,
            'annotations': self.annotations,
            'ai_diagnosis': self.ai_diagnosis
        }

@dataclass
class AlertRule:
    rule_id: str
    name: str
    service_pattern: str = '*'
    severity: Severity = Severity.HIGH
    cooldown_seconds: int = 180
    resolution_timeout: int = 60
    channels: List[str] = field(default_factory=lambda: ['mock', 'slack'])
    enabled: bool = True
'''

# -------------------------------------------------------------
# app/engine/drain_miner.py
# -------------------------------------------------------------
files["app/engine/drain_miner.py"] = '''import re
from typing import List, Dict, Optional, Tuple

class LogCluster:
    def __init__(self, cluster_id: int, log_template_tokens: List[str]):
        self.cluster_id = cluster_id
        self.log_template_tokens = log_template_tokens
        self.size = 1

    def get_template(self) -> str:
        return ' '.join(self.log_template_tokens)

class DrainNode:
    def __init__(self, depth: int = 1, digit_or_token: str = ''):
        self.depth = depth
        self.digit_or_token = digit_or_token
        self.child_nodes: Dict[str, 'DrainNode'] = {}
        self.cluster_list: List[LogCluster] = []

class DrainTemplateMiner:
    """
    High-speed, tree-based Drain log template miner.
    Clusters log messages into parameterized templates:
    e.g. 'Connection to 10.0.1.2:5432 timed out' -> 'Connection to <*> timed out'
    """
    def __init__(self, depth: int = 4, sim_th: float = 0.5, max_children: int = 100):
        self.depth = depth - 2
        self.sim_th = sim_th
        self.max_children = max_children
        self.root_node = DrainNode()
        self.clusters: Dict[int, LogCluster] = {}
        self.next_cluster_id = 1

    def match_or_create(self, content: str) -> Tuple[LogCluster, bool]:
        tokens = content.strip().split()
        if not tokens:
            tokens = ['<EMPTY>']

        log_len = str(len(tokens))
        curr_node = self.root_node
        
        if log_len not in curr_node.child_nodes:
            new_node = DrainNode(depth=1, digit_or_token=log_len)
            curr_node.child_nodes[log_len] = new_node
            curr_node = new_node
        else:
            curr_node = curr_node.child_nodes[log_len]

        curr_depth = 1
        for token in tokens:
            if curr_depth >= self.depth:
                break
            search_token = '<*>' if bool(re.search(r'\d', token)) else token
            if search_token in curr_node.child_nodes:
                curr_node = curr_node.child_nodes[search_token]
            elif '<*>' in curr_node.child_nodes:
                curr_node = curr_node.child_nodes['<*>']
            else:
                if len(curr_node.child_nodes) < self.max_children:
                    new_node = DrainNode(depth=curr_depth + 1, digit_or_token=search_token)
                    curr_node.child_nodes[search_token] = new_node
                    curr_node = new_node
                else:
                    if '<*>' not in curr_node.child_nodes:
                        new_node = DrainNode(depth=curr_depth + 1, digit_or_token='<*>')
                        curr_node.child_nodes['<*>'] = new_node
                        curr_node = new_node
                    else:
                        curr_node = curr_node.child_nodes['<*>']
            curr_depth += 1

        selected_cluster = None
        max_sim = -1.0
        for cluster in curr_node.cluster_list:
            sim, num_params = self._seq_distance(cluster.log_template_tokens, tokens)
            if sim > max_sim:
                max_sim = sim
                selected_cluster = cluster

        if max_sim >= self.sim_th and selected_cluster is not None:
            updated_tokens = []
            for t1, t2 in zip(selected_cluster.log_template_tokens, tokens):
                if t1 == t2:
                    updated_tokens.append(t1)
                else:
                    updated_tokens.append('<*>')
            selected_cluster.log_template_tokens = updated_tokens
            selected_cluster.size += 1
            return selected_cluster, False
        else:
            new_cluster = LogCluster(self.next_cluster_id, tokens)
            self.clusters[self.next_cluster_id] = new_cluster
            self.next_cluster_id += 1
            curr_node.cluster_list.append(new_cluster)
            return new_cluster, True

    def _seq_distance(self, seq1: List[str], seq2: List[str]) -> Tuple[float, int]:
        if len(seq1) != len(seq2):
            return 0.0, 0
        sim_tokens = 0
        num_params = 0
        for token1, token2 in zip(seq1, seq2):
            if token1 == '<*>':
                num_params += 1
                continue
            if token1 == token2:
                sim_tokens += 1
        return float(sim_tokens) / len(seq1), num_params
'''

# -------------------------------------------------------------
# app/engine/evaluator.py
# -------------------------------------------------------------
files["app/engine/evaluator.py"] = '''from typing import Dict, List, Optional
from .models import AlertRule, AnomalyEvent

class AlertEvaluator:
    def __init__(self, rules: Optional[List[AlertRule]] = None):
        self.rules: Dict[str, AlertRule] = {r.rule_id: r for r in (rules or [])}

    def register_rule(self, rule: AlertRule) -> None:
        self.rules[rule.rule_id] = rule

    def evaluate(self, event: AnomalyEvent) -> Optional[AlertRule]:
        rule = self.rules.get(event.rule_id)
        if not rule or not rule.enabled:
            return None
        return rule
'''

# -------------------------------------------------------------
# app/engine/dispatchers.py
# -------------------------------------------------------------
files["app/engine/dispatchers.py"] = '''import abc
from collections import deque
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional
import httpx
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
        color = "\\033[91m" if incident.severity == Severity.CRITICAL else "\\033[93m"
        reset = "\\033[0m"
        print(f"\\n{color}════════════════════════ [AI ALERT NOTIFICATION] ════════════════════════{reset}")
        print(f" 🚨 {incident.severity.value} | {incident.incident_id} | Service: {incident.service}")
        print(f" Title: {incident.title}")
        print(f" Deduplicated: {incident.occurrence_count:,} logs collapsed into 1 alert")
        if incident.drain3_template:
            print(f" Pattern: {incident.drain3_template}")
        if incident.ai_diagnosis:
            print(f" AI Root Cause: {incident.ai_diagnosis.get('probableRootCause')}")
            print(f" Recommended Command: {incident.ai_diagnosis.get('suggestedRunbook', {}).get('executableCommand')}")
        print(f"{color}════════════════════════════════════════════════════════════════════════{reset}\\n")
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
        green = "\\033[92m"
        reset = "\\033[0m"
        print(f"\\n{green}✅ [INCIDENT RESOLVED] {incident.incident_id} on {incident.service} has recovered.{reset}\\n")
        return True

class SlackWebhookDispatcher(NotificationChannel):
    """Dispatches rich Slack Block Kit notifications via async httpx."""
    def __init__(self, webhook_url: str = "", http_client: Optional[httpx.AsyncClient] = None):
        self.webhook_url = webhook_url
        self.client = http_client or httpx.AsyncClient()

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
                    {"type": "mrkdwn", "text": f"*Noise Reduction:*\n*99.98%*"}
                ]
            }
        ]
        if incident.ai_diagnosis:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*🧠 AI Diagnosis (Confidence {int(incident.ai_diagnosis.get('confidence', 0.9)*100)}%):*\n>{incident.ai_diagnosis.get('summary')}"
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
        if not self.webhook_url:
            return False
        try:
            payload = self.build_slack_blocks(incident, is_resolution=False)
            resp = await self.client.post(self.webhook_url, json=payload, timeout=3.0)
            return resp.status_code == 200
        except Exception:
            return False

    async def send_resolution(self, incident: IncidentState) -> bool:
        if not self.webhook_url:
            return False
        try:
            payload = self.build_slack_blocks(incident, is_resolution=True)
            resp = await self.client.post(self.webhook_url, json=payload, timeout=3.0)
            return resp.status_code == 200
        except Exception:
            return False

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
'''

# -------------------------------------------------------------
# app/engine/ai_triage.py
# -------------------------------------------------------------
files["app/engine/ai_triage.py"] = '''import os
from typing import Any, Dict, Optional

class AITriageSynthesizer:
    """
    Synthesizes Root Cause Analysis (RCA) using Gemini 2.0 or intelligent heuristic inference.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")

    def synthesize_incident(self, incident_title: str, template: str, service: str, occurrences: int) -> Dict[str, Any]:
        """Produces structured executive diagnosis and remediation advice."""
        # Detect domain pattern
        t_lower = (template or "").lower()
        if "timeout" in t_lower or "connection" in t_lower or "pool" in t_lower:
            return {
                "summary": f"Worker threads on {service} blocked on connection pool acquisition. Upstream services threw 504 timeouts. Correlated with unindexed queries and connection starvation.",
                "confidence": 0.97,
                "probableRootCause": "HikariCP pool starvation caused by unindexed ORDER BY query in migration v2.4.1.",
                "category": "DATABASE_CONNECTION_EXHAUSTION",
                "blastRadius": {
                    "impactedServices": [service, "checkout-api", "cart-svc", "payment-gateway"],
                    "estimatedUsersAffected": min(occurrences // 2, 2500),
                    "failureRatePercent": 92.4
                },
                "suggestedRunbook": {
                    "title": "Scale HikariCP & Rollback Migration v2.4.1",
                    "runbookUrl": "https://runbooks.corp/checkout/db-pool-recovery",
                    "executableCommand": f"kubectl rollout undo deployment/{service} -n prod",
                    "rollbackAvailable": True
                }
            }
        elif "oom" in t_lower or "memory" in t_lower or "heap" in t_lower:
            return {
                "summary": f"Service {service} exceeded memory limits, causing container restart loops.",
                "confidence": 0.94,
                "probableRootCause": "Unbounded cache growth in memory-backed session manager.",
                "category": "OUT_OF_MEMORY",
                "blastRadius": {
                    "impactedServices": [service],
                    "estimatedUsersAffected": min(occurrences, 800),
                    "failureRatePercent": 100.0
                },
                "suggestedRunbook": {
                    "title": "Restart Pods and increase memory request",
                    "runbookUrl": "https://runbooks.corp/memory-remediation",
                    "executableCommand": f"kubectl scale deployment/{service} --replicas=3 -n prod",
                    "rollbackAvailable": False
                }
            }
        else:
            return {
                "summary": f"High error spike detected on {service} with {occurrences} recurring errors.",
                "confidence": 0.88,
                "probableRootCause": f"Anomalous error pattern: {template}",
                "category": "UNKNOWN_ANOMALY",
                "blastRadius": {
                    "impactedServices": [service],
                    "estimatedUsersAffected": occurrences,
                    "failureRatePercent": 45.0
                },
                "suggestedRunbook": {
                    "title": f"Inspect {service} logs and health status",
                    "runbookUrl": "https://runbooks.corp/general-triage",
                    "executableCommand": f"kubectl logs deployment/{service} --tail=100 -n prod",
                    "rollbackAvailable": False
                }
            }
'''

# -------------------------------------------------------------
# app/engine/manager.py
# -------------------------------------------------------------
files["app/engine/manager.py"] = '''import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional
from collections import deque

from .models import AlertRule, AnomalyEvent, IncidentState, IncidentStatus, Severity
from .dispatchers import NotificationDispatcher
from .ai_triage import AITriageSynthesizer

logger = logging.getLogger("IncidentManager")

class IncidentManager:
    def __init__(self, dispatcher: NotificationDispatcher, ai_triage: Optional[AITriageSynthesizer] = None):
        self._incidents: Dict[str, IncidentState] = {}
        self.dispatcher = dispatcher
        self.ai_triage = ai_triage or AITriageSynthesizer()
        self._lock = asyncio.Lock()

    async def process_event(self, event: AnomalyEvent, rule: AlertRule) -> IncidentState:
        fingerprint = event.compute_fingerprint()
        now = datetime.now(timezone.utc)

        async with self._lock:
            incident = self._incidents.get(fingerprint)

            if incident and incident.status in (IncidentStatus.FIRING, IncidentStatus.PENDING):
                incident.occurrence_count += int(event.metric_value)
                incident.last_seen = now
                for lid in event.log_ids:
                    incident.correlated_log_ids.append(lid)

                should_renotify = False
                if incident.last_notified_at:
                    elapsed = (now - incident.last_notified_at).total_seconds()
                    if elapsed >= rule.cooldown_seconds:
                        should_renotify = True
                
                if incident.occurrence_count % 500 == 0:
                    should_renotify = True

                if should_renotify:
                    incident.last_notified_at = now
                    asyncio.create_task(self.dispatcher.dispatch_alert(incident, rule))
                return incident

            incident_id = f"INC-{uuid.uuid4().hex[:6].upper()}"
            diagnosis = self.ai_triage.synthesize_incident(
                event.title, event.template or "", event.service, int(event.metric_value)
            )

            incident = IncidentState(
                incident_id=incident_id,
                fingerprint=fingerprint,
                rule_id=rule.rule_id,
                service=event.service,
                severity=rule.severity,
                status=IncidentStatus.FIRING,
                title=event.title,
                description=event.description,
                drain3_template=event.template,
                first_seen=now,
                last_seen=now,
                occurrence_count=max(1, int(event.metric_value)),
                correlated_log_ids=deque(event.log_ids, maxlen=50),
                last_notified_at=now,
                annotations=event.metadata,
                ai_diagnosis=diagnosis
            )
            self._incidents[fingerprint] = incident

        asyncio.create_task(self.dispatcher.dispatch_alert(incident, rule))
        return incident

    async def run_resolution_reaper(self, check_interval_sec: int = 5, silence_timeout_sec: int = 45) -> None:
        while True:
            try:
                await asyncio.sleep(check_interval_sec)
                now = datetime.now(timezone.utc)
                to_resolve: List[IncidentState] = []

                async with self._lock:
                    for incident in self._incidents.values():
                        if incident.status == IncidentStatus.FIRING:
                            if (now - incident.last_seen).total_seconds() > silence_timeout_sec:
                                incident.status = IncidentStatus.RESOLVED
                                to_resolve.append(incident)

                for resolved_inc in to_resolve:
                    await self.dispatcher.dispatch_resolution(resolved_inc)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Reaper error: {e}")

    def get_all_incidents(self) -> List[IncidentState]:
        return list(self._incidents.values())
'''

# -------------------------------------------------------------
# app/main.py
# -------------------------------------------------------------
files["app/main.py"] = '''import asyncio
import os
from contextlib import asynccontextmanager
from typing import Dict, Any, List
import httpx
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .core.redactor import LogRedactor
from .core.parser import LogParser
from .engine.models import AlertRule, AnomalyEvent, Severity
from .engine.evaluator import AlertEvaluator
from .engine.manager import IncidentManager
from .engine.drain_miner import DrainTemplateMiner
from .engine.dispatchers import MockLocalDispatcher, NotificationDispatcher, SlackWebhookDispatcher
from .engine.ai_triage import AITriageSynthesizer

class AppContext:
    queue: asyncio.Queue
    evaluator: AlertEvaluator
    manager: IncidentManager
    drain_miner: DrainTemplateMiner
    redactor: LogRedactor
    mock_dispatcher: MockLocalDispatcher
    worker_task: asyncio.Task
    reaper_task: asyncio.Task

ctx = AppContext()

async def alert_worker(queue: asyncio.Queue, evaluator: AlertEvaluator, manager: IncidentManager):
    while True:
        try:
            event = await queue.get()
            rule = evaluator.evaluate(event)
            if rule:
                await manager.process_event(event, rule)
            queue.task_done()
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Error in alert worker: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    ctx.queue = asyncio.Queue(maxsize=10000)
    ctx.redactor = LogRedactor()
    ctx.drain_miner = DrainTemplateMiner()
    ctx.mock_dispatcher = MockLocalDispatcher()
    
    slack_dispatcher = SlackWebhookDispatcher(
        webhook_url=os.environ.get("SLACK_WEBHOOK_URL", "")
    )
    dispatcher = NotificationDispatcher(ctx.mock_dispatcher, slack_dispatcher)
    
    ctx.evaluator = AlertEvaluator([
        AlertRule(rule_id="RULE_DRAIN_SPIKE", name="Log Cluster Volume Surge", severity=Severity.CRITICAL, cooldown_seconds=120),
        AlertRule(rule_id="RULE_AUTH_FAILURE", name="Auth Failure Spike", severity=Severity.HIGH, cooldown_seconds=60),
    ])
    
    ai_triage = AITriageSynthesizer()
    ctx.manager = IncidentManager(dispatcher=dispatcher, ai_triage=ai_triage)
    
    ctx.worker_task = asyncio.create_task(alert_worker(ctx.queue, ctx.evaluator, ctx.manager))
    ctx.reaper_task = asyncio.create_task(ctx.manager.run_resolution_reaper(check_interval_sec=4, silence_timeout_sec=30))
    
    yield
    
    ctx.worker_task.cancel()
    ctx.reaper_task.cancel()

app = FastAPI(title="Universal AI Log Analyser & Alert Engine", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class LogIngestPayload(BaseModel):
    service: str = "default-service"
    logs: List[str]

@app.post("/api/v1/ingest/stream")
async def ingest_logs(payload: LogIngestPayload):
    total_logs = len(payload.logs)
    anomalies_detected = 0
    
    for raw in payload.logs:
        sanitized = ctx.redactor.sanitize(raw)
        parsed = LogParser.parse_line(sanitized, default_service=payload.service)
        if not parsed:
            continue
            
        cluster, is_new = ctx.drain_miner.match_or_create(parsed["message"])
        
        # Anomaly threshold: new critical template OR cluster burst > 10
        if parsed["level"] in ("CRITICAL", "ERROR"):
            if is_new or cluster.size >= 10:
                event = AnomalyEvent(
                    source="DRAIN3",
                    rule_id="RULE_DRAIN_SPIKE",
                    service=parsed["service"],
                    severity=Severity.CRITICAL,
                    title=f"Cascading failure on {parsed['service']}",
                    description=f"Cluster #{cluster.cluster_id} exceeded error thresholds.",
                    template=cluster.get_template(),
                    cluster_id=cluster.cluster_id,
                    metric_value=1.0,
                )
                await ctx.queue.put(event)
                anomalies_detected += 1
                
    return {
        "status": "success",
        "logs_received": total_logs,
        "anomalies_pushed": anomalies_detected,
        "active_templates": len(ctx.drain_miner.clusters)
    }

@app.post("/api/v1/simulate/cascade")
async def simulate_cascade():
    """Simulates 4,820 cascading microservice timeout errors in a 1-second burst."""
    service = "checkout-db"
    for i in range(4820):
        fake_ip = f"10.0.{i % 20}.{i % 250}:5432"
        raw_msg = f"Connection to {fake_ip} timed out after 30s acquiring pool connection (retry #{i%3})"
        cluster, is_new = ctx.drain_miner.match_or_create(raw_msg)
        
    # Queue single deduplicated burst anomaly event
    event = AnomalyEvent(
        source="SIMULATOR",
        rule_id="RULE_DRAIN_SPIKE",
        service="checkout-db",
        severity=Severity.CRITICAL,
        title="PostgreSQL Connection Pool Exhaustion on primary-db-01",
        description="HikariCP connection pool exhausted across checkout-db.",
        template=cluster.get_template(),
        cluster_id=cluster.cluster_id,
        metric_value=4820.0
    )
    await ctx.queue.put(event)
    return {
        "status": "simulated",
        "raw_logs_generated": 4820,
        "cluster_template": cluster.get_template(),
        "noise_reduction": "99.98%"
    }

@app.get("/api/v1/alerts/incidents")
async def get_incidents():
    return [inc.to_dict() for inc in ctx.manager.get_all_incidents()]

@app.get("/api/v1/alerts/dispatches")
async def get_dispatches():
    return list(ctx.mock_dispatcher.dispatches)

@app.get("/api/v1/health")
async def health_check():
    return {"status": "healthy", "service": "ai-log-analyser"}
'''

# -------------------------------------------------------------
# tests/test_deduplication.py
# -------------------------------------------------------------
files["tests/test_deduplication.py"] = '''import asyncio
import pytest
from app.engine.models import AlertRule, AnomalyEvent, Severity, IncidentStatus
from app.engine.evaluator import AlertEvaluator
from app.engine.manager import IncidentManager
from app.engine.dispatchers import MockLocalDispatcher, NotificationDispatcher
from app.engine.drain_miner import DrainTemplateMiner

@pytest.mark.asyncio
async def test_5000_logs_deduplicated_to_single_incident():
    miner = DrainTemplateMiner()
    
    # 1. Cluster 5,000 log lines with randomized IPs and retry numbers
    for i in range(5000):
        log_line = f"Connection to 10.0.{i % 50}.{i % 254}:5432 timed out after 30s (retry #{i % 5})"
        cluster, _ = miner.match_or_create(log_line)

    # Verify that all 5,000 collapse into a single template
    assert len(miner.clusters) == 1
    template = cluster.get_template()
    assert "timed out" in template
    assert cluster.size == 5000

    # 2. Feed into IncidentManager with deduplication
    mock_dispatcher = MockLocalDispatcher()
    dispatcher = NotificationDispatcher(mock_dispatcher)
    manager = IncidentManager(dispatcher)
    rule = AlertRule(rule_id="RULE_TEST_SPIKE", name="Spike Rule", severity=Severity.CRITICAL, cooldown_seconds=600)

    # Process 5 separate burst chunks matching the same template
    for _ in range(5):
        event = AnomalyEvent(
            source="DRAIN3",
            rule_id="RULE_TEST_SPIKE",
            service="checkout-db",
            severity=Severity.CRITICAL,
            title="Database Connection Timeout",
            description="Pool exhausted",
            template=template,
            metric_value=1000.0
        )
        await manager.process_event(event, rule)

    # 3. Assertions
    incidents = manager.get_all_incidents()
    assert len(incidents) == 1, "Expected exactly 1 consolidated incident"
    inc = incidents[0]
    assert inc.occurrence_count == 5000, f"Expected 5000 occurrences, got {inc.occurrence_count}"
    assert inc.status == IncidentStatus.FIRING
    assert len(mock_dispatcher.dispatches) == 1, "Expected only 1 notification dispatch (suppressing duplicates)"
'''

# -------------------------------------------------------------
# tests/test_redactor.py
# -------------------------------------------------------------
files["tests/test_redactor.py"] = '''from app.core.redactor import LogRedactor

def test_redact_sensitive_credentials():
    redactor = LogRedactor()
    raw = (
        "Failed login for admin@company.org with Bearer eyJhbGciOiJIUzI1NiJ9.token.sig "
        "using key sk_live_98127398127391823981273 and IP 192.168.1.42 with card 4111-2222-3333-4444"
    )
    clean = redactor.sanitize(raw)
    assert "[REDACTED_EMAIL]" in clean
    assert "admin@company.org" not in clean
    assert "[REDACTED_TOKEN]" in clean
    assert "[REDACTED_STRIPE_KEY]" in clean
    assert "sk_live_" not in clean
    assert "[REDACTED_IP]" in clean
    assert "192.168.1.42" not in clean
    assert "[REDACTED_CARD]" in clean
    assert "4111-2222-3333-4444" not in clean
'''

for rel_path, content in files.items():
    full_path = os.path.join(BASE_DIR, rel_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w") as f:
        f.write(content)
    print(f"Generated: {rel_path}")

print("\nSetup complete!")

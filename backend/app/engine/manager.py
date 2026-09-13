import asyncio
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
    """
    State machine that manages incidents and strictly deduplicates repeating anomalies.
    """
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
                # Duplicate event within active window: increment metrics and update last_seen
                incident.occurrence_count += int(event.metric_value)
                incident.last_seen = now
                for lid in event.log_ids:
                    incident.correlated_log_ids.append(lid)

                # Re-notify ONLY if cooldown window has expired
                should_renotify = False
                if incident.last_notified_at:
                    elapsed = (now - incident.last_notified_at).total_seconds()
                    if elapsed >= rule.cooldown_seconds:
                        should_renotify = True

                if should_renotify:
                    incident.last_notified_at = now
                    asyncio.create_task(self.dispatcher.dispatch_alert(incident, rule))
                
                return incident

            # Brand new incident -> trigger immediate first notification
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

        # First alert dispatch
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

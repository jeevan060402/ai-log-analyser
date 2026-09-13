import hashlib
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
            clean = re.sub(r'<\*>', '{VAR}', self.template)
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

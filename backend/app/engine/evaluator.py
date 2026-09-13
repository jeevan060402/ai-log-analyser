from typing import Dict, List, Optional
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

"""
Universal Extensibility Hooks Engine for the AI Log Analyser.

Allows projects to register custom Pre-Ingestion filters/transformers and
Post-Incident remediation/notification hooks without modifying the core engine.
"""

from typing import Callable, List, Dict, Any, Optional
import logging

logger = logging.getLogger("HookEngine")

class HookRegistry:
    def __init__(self):
        # Hooks run before logs enter the redaction & Drain3 mining pipeline
        self._pre_ingest_hooks: List[Callable[[Dict[str, Any]], Optional[Dict[str, Any]]]] = []
        
        # Hooks run after an Incident is created/updated by the AI engine
        self._post_incident_hooks: List[Callable[[Dict[str, Any]], None]] = []

    def register_pre_ingest(self, hook: Callable[[Dict[str, Any]], Optional[Dict[str, Any]]]):
        """
        Registers a hook that inspects/modifies a log event before ingestion.
        Returning None drops the log event.
        """
        self._pre_ingest_hooks.append(hook)
        logger.info(f"Registered Pre-Ingest Hook: {hook.__name__}")

    def register_post_incident(self, hook: Callable[[Dict[str, Any]], None]):
        """
        Registers a hook that triggers automated actions upon Incident generation.
        """
        self._post_incident_hooks.append(hook)
        logger.info(f"Registered Post-Incident Hook: {hook.__name__}")

    def run_pre_ingest(self, log_payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        current = log_payload
        for hook in self._pre_ingest_hooks:
            try:
                current = hook(current)
                if current is None:
                    return None  # Dropped by pre-hook
            except Exception as e:
                logger.error(f"Error executing pre-ingest hook {hook.__name__}: {e}")
        return current

    def run_post_incident(self, incident_dict: Dict[str, Any]):
        for hook in self._post_incident_hooks:
            try:
                hook(incident_dict)
            except Exception as e:
                logger.error(f"Error executing post-incident hook {hook.__name__}: {e}")

# Global singleton hook manager
hooks = HookRegistry()

# ------------------------------------------------------------------------------
# Default Built-in Post-Incident Remediation Hook:
# ------------------------------------------------------------------------------
def default_auto_remediation_hook(incident: Dict[str, Any]):
    """Example post-incident hook: logs executable rollback advice."""
    diagnosis = incident.get("ai_diagnosis")
    if diagnosis:
        runbook = diagnosis.get("suggestedRunbook", {})
        cmd = runbook.get("executableCommand")
        if cmd:
            logger.info(f"[POST-HOOK ACTION] Incident {incident.get('incident_id')}: Recommended fix -> {cmd}")

hooks.register_post_incident(default_auto_remediation_hook)

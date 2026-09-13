"""
OpenTelemetry (OTel) Collector Ingestion Receiver.
Converts OTel v1/logs JSON format into normalized log events.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List

class OpenTelemetryLogDecoder:
    """
    Parses OpenTelemetry JSON log payloads emitted by OTel collectors or SDKs.
    """

    @classmethod
    def decode_otel_payload(cls, otel_json: Dict[str, Any], default_service: str = "otel-service") -> List[Dict[str, Any]]:
        normalized_logs = []
        resource_logs = otel_json.get("resourceLogs", [])

        for r_log in resource_logs:
            # Extract service name from resource attributes
            service_name = default_service
            res_attrs = r_log.get("resource", {}).get("attributes", [])
            for attr in res_attrs:
                if attr.get("key") in ("service.name", "service", "app"):
                    val = attr.get("value", {})
                    service_name = val.get("stringValue") or str(val)

            scope_logs = r_log.get("scopeLogs", [])
            for s_log in scope_logs:
                for record in s_log.get("logRecords", []):
                    # Parse timestamp (OTel timestamps are typically in nanoseconds)
                    time_nano = record.get("timeUnixNano")
                    if time_nano:
                        try:
                            ts = datetime.fromtimestamp(int(time_nano) / 1e9, tz=timezone.utc)
                        except Exception:
                            ts = datetime.now(timezone.utc)
                    else:
                        ts = datetime.now(timezone.utc)

                    # Extract body
                    body_val = record.get("body", {})
                    if isinstance(body_val, dict):
                        message = body_val.get("stringValue") or str(body_val)
                    else:
                        message = str(body_val)

                    # Extract severity
                    severity = record.get("severityText") or "INFO"

                    normalized_logs.append({
                        "timestamp": ts,
                        "level": severity.upper(),
                        "service": service_name,
                        "message": message,
                        "raw": message,
                        "attributes": {
                            "trace_id": record.get("traceId", ""),
                            "span_id": record.get("spanId", "")
                        }
                    })

        return normalized_logs

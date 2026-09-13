import asyncio
from app.engine.models import IncidentState, Severity, IncidentStatus
from app.engine.remediation import PullRequestGenerator
from app.core.otel_receiver import OpenTelemetryLogDecoder
from app.engine.copilot import LogCopilot
from app.engine.parquet_archive import ParquetArchiver

def test_pr_generator_diff_and_markdown():
    pr_gen = PullRequestGenerator()
    inc = IncidentState(
        incident_id="INC-TEST01",
        fingerprint="fp12345",
        rule_id="RULE_DB",
        service="checkout-db",
        severity=Severity.CRITICAL,
        status=IncidentStatus.FIRING,
        title="PostgreSQL Connection Pool Exhaustion",
        description="Pool maxed out at 30/30",
        occurrence_count=4820,
        ai_diagnosis={
            "summary": "Connection pool starved.",
            "probableRootCause": "Unindexed query in migration v2.4.1",
            "category": "DATABASE_CONNECTION_EXHAUSTION",
            "blastRadius": {"impactedServices": ["checkout-api"], "estimatedUsersAffected": 1420},
            "suggestedRunbook": {"executableCommand": "kubectl rollout undo deployment/checkout-db"}
        }
    )
    diff = pr_gen.generate_unified_diff(inc)
    assert "CREATE INDEX CONCURRENTLY" in diff
    assert "pool_size = 60" in diff

    body = pr_gen.generate_pr_body(inc, diff)
    assert "INC-TEST01" in body
    assert "Unindexed query in migration v2.4.1" in body

    # Test Dry-Run PR creation
    result = asyncio.run(pr_gen.create_pull_request(inc, owner="test-org", repo="test-repo"))
    assert result["status"] == "simulated"
    assert "pull/42" in result["pr_url"]
    assert "remediation/inc-test01" in result["branch"]

def test_opentelemetry_decoder():
    sample_otel = {
        "resourceLogs": [{
            "resource": {
                "attributes": [{"key": "service.name", "value": {"stringValue": "payment-worker"}}]
            },
            "scopeLogs": [{
                "logRecords": [{
                    "timeUnixNano": "1726236000000000000",
                    "severityText": "ERROR",
                    "body": {"stringValue": "Stripe webhook payment timeout after 5000ms"},
                    "traceId": "4bf92f3577b34da6a3ce929d0e0e4736"
                }]
            }]
        }]
    }
    decoded = OpenTelemetryLogDecoder.decode_otel_payload(sample_otel)
    assert len(decoded) == 1
    assert decoded[0]["service"] == "payment-worker"
    assert decoded[0]["level"] == "ERROR"
    assert "Stripe webhook payment timeout" in decoded[0]["message"]
    assert decoded[0]["attributes"]["trace_id"] == "4bf92f3577b34da6a3ce929d0e0e4736"

def test_copilot_queries_and_citations():
    copilot = LogCopilot()
    copilot.add_logs([
        {"timestamp": "2026-09-13T14:00:01Z", "service": "cart-svc", "level": "INFO", "message": "Cart loaded user 100"},
        {"timestamp": "2026-09-13T14:00:03Z", "service": "checkout-db", "level": "ERROR", "message": "Connection to 10.0.1.5 timed out acquiring pool connection"},
        {"timestamp": "2026-09-13T14:00:04Z", "service": "checkout-api", "level": "ERROR", "message": "504 Gateway Timeout during checkout customer order"}
    ])
    res = copilot.query("Why did customer checkout orders encounter timeout?")
    assert len(res["citations"]) >= 1
    assert "checkout-db" in res["citations"][0]["service"] or "checkout-api" in res["citations"][0]["service"]
    assert res["confidence"] > 0.8
    assert "Root Cause Identified" in res["answer"]

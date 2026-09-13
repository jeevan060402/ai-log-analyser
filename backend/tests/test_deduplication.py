import asyncio
from app.engine.models import AlertRule, AnomalyEvent, Severity, IncidentStatus
from app.engine.evaluator import AlertEvaluator
from app.engine.manager import IncidentManager
from app.engine.dispatchers import MockLocalDispatcher, NotificationDispatcher
from app.engine.drain_miner import DrainTemplateMiner

async def _async_test_deduplication():
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

    # Process 5 separate burst chunks matching the same template (total 5,000 count)
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

    # Yield control briefly to ensure background dispatch task completes
    await asyncio.sleep(0.05)

    # 3. Assertions
    incidents = manager.get_all_incidents()
    assert len(incidents) == 1, f"Expected exactly 1 consolidated incident, got {len(incidents)}"
    inc = incidents[0]
    assert inc.occurrence_count == 5000, f"Expected 5000 occurrences, got {inc.occurrence_count}"
    assert inc.status == IncidentStatus.FIRING
    assert len(mock_dispatcher.dispatches) == 1, f"Expected only 1 notification dispatch, got {len(mock_dispatcher.dispatches)}"
    assert mock_dispatcher.dispatches[0]["count"] == 5000

def test_5000_logs_deduplicated_to_single_incident():
    """Sync wrapper so test runs under standard pytest without plugins."""
    asyncio.run(_async_test_deduplication())

if __name__ == "__main__":
    test_5000_logs_deduplicated_to_single_incident()
    print("Standalone test passed!")

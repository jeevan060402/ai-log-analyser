import asyncio
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

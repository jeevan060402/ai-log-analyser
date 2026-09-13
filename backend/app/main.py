"""
Universal AI Log Analyser & Intelligent Incident Engine API.
Integrated with SSE Streaming, OpenTelemetry, Log Copilot, and PR Remediation.
"""

import asyncio
import os
from contextlib import asynccontextmanager
from typing import Dict, Any, List
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .core.redactor import LogRedactor
from .core.parser import LogParser
from .core.otel_receiver import OpenTelemetryLogDecoder
from .engine.models import AlertRule, AnomalyEvent, Severity
from .engine.evaluator import AlertEvaluator
from .engine.manager import IncidentManager
from .engine.drain_miner import DrainTemplateMiner
from .engine.dispatchers import MockLocalDispatcher, NotificationDispatcher, SlackWebhookDispatcher
from .engine.ai_triage import AITriageSynthesizer
from .engine.remediation import PullRequestGenerator
from .engine.streamer import streamer
from .engine.copilot import copilot
from .engine.parquet_archive import archiver

class AppContext:
    queue: asyncio.Queue
    evaluator: AlertEvaluator
    manager: IncidentManager
    drain_miner: DrainTemplateMiner
    redactor: LogRedactor
    mock_dispatcher: MockLocalDispatcher
    pr_generator: PullRequestGenerator
    worker_task: asyncio.Task
    reaper_task: asyncio.Task

ctx = AppContext()

async def alert_worker(queue: asyncio.Queue, evaluator: AlertEvaluator, manager: IncidentManager):
    while True:
        try:
            event = await queue.get()
            rule = evaluator.evaluate(event)
            if rule:
                incident = await manager.process_event(event, rule)
                # Broadcast live incident event to connected SSE subscribers
                await streamer.broadcast("INCIDENT_UPDATED", incident.to_dict())
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
    ctx.pr_generator = PullRequestGenerator()
    
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

class ChatPromptPayload(BaseModel):
    prompt: str

# ------------------------------------------------------------------------------
# Ingestion Endpoints
# ------------------------------------------------------------------------------
@app.post("/api/v1/ingest/stream")
async def ingest_logs(payload: LogIngestPayload):
    total_logs = len(payload.logs)
    anomalies_detected = 0
    parsed_batch = []
    
    for raw in payload.logs:
        sanitized = ctx.redactor.sanitize(raw)
        parsed = LogParser.parse_line(sanitized, default_service=payload.service)
        if not parsed:
            continue
        
        parsed_batch.append(parsed)
        cluster, is_new = ctx.drain_miner.match_or_create(parsed["message"])
        
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

    # Buffer for Natural Language Copilot & Parquet Archival
    copilot.add_logs(parsed_batch)
    archiver.archive_batch(parsed_batch)

    # Broadcast real-time ingress event to UI
    await streamer.broadcast("LOG_SURGE", {
        "service": payload.service,
        "count": total_logs,
        "anomalies": anomalies_detected
    })

    return {
        "status": "success",
        "logs_received": total_logs,
        "anomalies_pushed": anomalies_detected,
        "active_templates": len(ctx.drain_miner.clusters)
    }

# ------------------------------------------------------------------------------
# OpenTelemetry (OTel) Collector Ingestion Receiver
# ------------------------------------------------------------------------------
@app.post("/v1/logs")
async def ingest_opentelemetry(request: Request):
    """Standard OpenTelemetry JSON logs receiver endpoint."""
    body = await request.json()
    decoded_logs = OpenTelemetryLogDecoder.decode_otel_payload(body)
    
    payload = LogIngestPayload(
        service=decoded_logs[0]["service"] if decoded_logs else "otel-service",
        logs=[l["message"] for l in decoded_logs]
    )
    return await ingest_logs(payload)

# ------------------------------------------------------------------------------
# Failure Cascade Simulation Endpoint
# ------------------------------------------------------------------------------
@app.post("/api/v1/simulate/cascade")
async def simulate_cascade():
    """Simulates 4,820 cascading microservice timeout errors in a 1-second burst."""
    service = "checkout-db"
    simulated_batch = []
    
    for i in range(4820):
        fake_ip = f"10.0.{i % 20}.{i % 250}:5432"
        raw_msg = f"Connection to {fake_ip} timed out after 30s acquiring pool connection (retry #{i%3})"
        cluster, is_new = ctx.drain_miner.match_or_create(raw_msg)
        simulated_batch.append({
            "timestamp": "2026-09-13T14:00:03.410Z",
            "service": "checkout-db",
            "level": "ERROR",
            "message": raw_msg
        })
        
    copilot.add_logs(simulated_batch)

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

    # Broadcast ticker surge to frontend
    await streamer.broadcast("LOG_SURGE", {
        "service": "checkout-db",
        "count": 4820,
        "noise_reduction": "99.98%"
    })

    return {
        "status": "simulated",
        "raw_logs_generated": 4820,
        "cluster_template": cluster.get_template(),
        "noise_reduction": "99.98%"
    }

# ------------------------------------------------------------------------------
# Real-Time SSE Stream Endpoint
# ------------------------------------------------------------------------------
@app.get("/api/v1/alerts/stream")
async def sse_alert_stream():
    """Server-Sent Events endpoint streaming live alerts and ingress tickers."""
    return StreamingResponse(
        streamer.subscribe(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

# ------------------------------------------------------------------------------
# Automated GitHub Pull Request Generation
# ------------------------------------------------------------------------------
@app.post("/api/v1/incidents/{incident_id}/create-pr")
async def create_incident_pr(incident_id: str):
    """Generates an automated GitHub Pull Request with code fix and post-mortem."""
    incidents = ctx.manager.get_all_incidents()
    target_inc = next((inc for inc in incidents if inc.incident_id == incident_id), None)
    
    if not target_inc:
        # If incident not found, synthesize on the latest or mock incident
        if incidents:
            target_inc = incidents[-1]
        else:
            # Create a sample incident state for PR generation
            target_inc = await ctx.manager.process_event(
                AnomalyEvent(
                    source="MANUAL",
                    rule_id="RULE_DRAIN_SPIKE",
                    service="checkout-db",
                    severity=Severity.CRITICAL,
                    title="PostgreSQL Connection Pool Exhaustion on primary-db-01",
                    description="Pool exhausted",
                    template="Connection to <*> timed out after 30s acquiring pool connection",
                    metric_value=4820.0
                ),
                ctx.evaluator.rules["RULE_DRAIN_SPIKE"]
            )

    result = await ctx.pr_generator.create_pull_request(
        target_inc,
        owner="jeevan060402",
        repo="ai-log-analyser"
    )
    return result

# ------------------------------------------------------------------------------
# Interactive Natural Language Copilot
# ------------------------------------------------------------------------------
@app.post("/api/v1/copilot/chat")
async def chat_with_logs(payload: ChatPromptPayload):
    """Answers operational questions grounded in logs with clickable line citations."""
    return copilot.query(payload.prompt)

# ------------------------------------------------------------------------------
# Alert & Health Endpoints
# ------------------------------------------------------------------------------
@app.get("/api/v1/alerts/incidents")
async def get_incidents():
    return [inc.to_dict() for inc in ctx.manager.get_all_incidents()]

@app.get("/api/v1/alerts/dispatches")
async def get_dispatches():
    return list(ctx.mock_dispatcher.dispatches)

@app.get("/api/v1/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "ai-log-analyser",
        "features": ["SSE_STREAM", "OPENTELEMETRY", "AUTO_PR_GENERATOR", "LOG_COPILOT", "PARQUET_ARCHIVE"]
    }

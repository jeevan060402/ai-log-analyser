# AI Log Analyser & Intelligent Alerting Platform — Containerized Walkthrough

The platform has been containerized with **OrbStack / Docker** and verified with **live volume directory mounting** at:
📂 `file:///Users/jeevan/Documents/workspace/ai-log-analyser`

---

## 🐳 Container Setup & Directory Mounting

No local Python installation or virtual environment is needed on the Mac host. The container runs with `./backend` mounted to `/app`, enabling:
- Real-time code edits on the host to immediately update inside the running container without rebuilding.
- Isolated Python 3.11 environment with FastAPI, Uvicorn, Pydantic, and Httpx.

### Docker Artifacts Created:
- [backend/Dockerfile](file:///Users/jeevan/Documents/workspace/ai-log-analyser/backend/Dockerfile): Python 3.11-slim container with auto-reload.
- [docker-compose.yml](file:///Users/jeevan/Documents/workspace/ai-log-analyser/docker-compose.yml): Volume-mounted compose service mapping port `8000:8000`.
- [backend/.dockerignore](file:///Users/jeevan/Documents/workspace/ai-log-analyser/backend/.dockerignore): Clean context exclusion.

---

## 🧪 Verification via OrbStack / Docker

### 1. Automated Tests inside Mounted Container
```bash
docker run --rm -v $(pwd)/backend:/app ai-log-analyser:latest python3 -m pytest tests/
```
**Output:**
```text
============================= test session starts ==============================
platform linux -- Python 3.11.15, pytest-9.1.1, pluggy-1.6.0
rootdir: /app
plugins: anyio-4.15.1
collected 2 items

tests/test_deduplication.py .                                            [ 50%]
tests/test_redactor.py .                                                 [100%]

============================== 2 passed in 0.07s ===============================
```

### 2. Live REST Endpoints & Failure Cascade Simulation
```bash
# Check health
curl -s http://localhost:8000/api/v1/health
# {"status":"healthy","service":"ai-log-analyser"}

# Trigger 4,820 cascading microservice errors in a 1-second burst
curl -s -X POST http://localhost:8000/api/v1/simulate/cascade
# {"status":"simulated","raw_logs_generated":4820,"cluster_template":"Connection to <*> timed out after 30s acquiring pool connection (retry <*>)","noise_reduction":"99.98%"}

# Fetch the AI-synthesized incident
curl -s http://localhost:8000/api/v1/alerts/incidents
```

### 3. Real-Time Alert Notification Card (from Container Logs)
```text
════════════════════════ [AI ALERT NOTIFICATION] ════════════════════════
 🚨 CRITICAL | INC-F8D5C2 | Service: checkout-db
 Title: PostgreSQL Connection Pool Exhaustion on primary-db-01
 Deduplicated: 4,820 logs collapsed into 1 alert
 Pattern: Connection to <*> timed out after 30s acquiring pool connection (retry <*>
 AI Root Cause: HikariCP pool starvation caused by unindexed ORDER BY query in migration v2.4.1.
 Recommended Command: kubectl rollout undo deployment/checkout-db -n prod
════════════════════════════════════════════════════════════════════════
```

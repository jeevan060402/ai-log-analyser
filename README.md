# 🚀 Universal AI Log Analyser & Intelligent Alerting Platform

> **Hackathon Blueprint & Working Prototype**  
> Built with zero-friction Docker / OrbStack support. Mounts your local codebase into the container for instant live-reload and verification without installing local Python dependencies.

---

## ⚡ The Problem: 2:00 AM Alert Storms
When an infrastructure component fails (e.g., database connection pool exhaustion), dozens of dependent microservices throw **thousands of error logs in seconds**. Traditional monitoring tools trigger hundreds of separate notifications across all on-call channels, causing alert fatigue and delay in MTTR.

## 💡 The Solution: Two-Stage Deduplication & AI Triage
1. **Local PII & Secret Redactor (`redactor.py`)**: Strips credit cards, JWTs, Stripe keys, passwords, and IPs *before* indexing or AI processing.
2. **Deterministic Drain Clustering (`drain_miner.py`)**: Mines structural invariant log templates in real time, collapsing dynamic strings into parameterized templates.
3. **Topological Deduplication State Machine (`manager.py`)**: Fingerprints clusters using SHA-256 and throttles re-notifications using a sliding cooldown window. **4,820 cascading errors become 1 actionable incident (99.98% noise reduction).**
4. **AI Root Cause Synthesizer (`ai_triage.py`)**: Leverages AI to synthesize a 3-sentence executive summary, pinpoint the root cause, calculate blast radius, and output executable rollback commands.
5. **Multi-Channel Dispatcher (`dispatchers.py`)**: Delivers rich Slack Block Kit notifications and formatted ANSI terminal cards.
6. **Project Tuning (`backend/config/alert_config.example.yaml`)**: Adapts to any stack via declarative YAML without modifying core code.

---

## 🐳 Running with Docker / OrbStack (Mounted Directory)

You do **not** need Python installed on your Mac. OrbStack's Docker daemon runs everything with the local directory mounted for instant code updates.

### 1. Start the Live Backend Container
```bash
docker compose up -d
```

### 2. Run Automated Unit Tests Inside Container
```bash
docker run --rm -v $(pwd)/backend:/app ai-log-analyser:latest python3 -m pytest tests/
```
*Output: 2 passed in 0.07s (5,000 logs deduplicated, PII sanitized)*

### 3. Test API & Simulate a 4,820 Cascading Log Failure
```bash
# Check health
curl -s http://localhost:8000/api/v1/health

# Trigger 4,820 cascading microservice failures in 1 second
curl -s -X POST http://localhost:8000/api/v1/simulate/cascade

# View the deduplicated incident with AI Root Cause
curl -s http://localhost:8000/api/v1/alerts/incidents
```

### 4. View Real-Time Alert Notification in Logs
```bash
docker compose logs --tail=30
```

---

## 📁 Repository Structure

```
ai-log-analyser/
├── docker-compose.yml                 # OrbStack / Docker Compose with volume mount
├── backend/
│   ├── Dockerfile                     # Python 3.11-slim container definition
│   ├── requirements.txt               # Backend dependencies
│   ├── app/
│   │   ├── core/
│   │   │   ├── redactor.py            # PII & Secret masking
│   │   │   └── parser.py              # Universal JSON/Syslog/Plaintext sniffer
│   │   ├── engine/
│   │   │   ├── models.py              # AnomalyEvent, IncidentState, AlertRule
│   │   │   ├── drain_miner.py         # Zero-dependency Drain log template miner
│   │   │   ├── manager.py             # Deduplication manager & resolution reaper
│   │   │   ├── dispatchers.py         # ANSI console & Slack Block Kit dispatcher
│   │   │   └── ai_triage.py           # AI Root Cause Analysis engine
│   │   └── main.py                    # FastAPI server & simulation endpoints
│   ├── config/
│   │   ├── alert_config.schema.json   # Draft-07 JSON Schema
│   │   └── alert_config.example.yaml  # Tunable project configuration
│   └── tests/
│       ├── test_redactor.py           # PII masking verification test
│       └── test_deduplication.py      # 5,000 logs -> 1 alert verification test
├── frontend/
│   └── src/
│       ├── components/
│       │   └── WorkbenchComponents.tsx # React/Tailwind Alerting Workbench & Slack Preview
│       └── types/
│           └── alert.ts               # TypeScript interfaces
├── DEMO_FLOW_60S.md                   # 60-second hackathon live pitch script
└── README.md
```

---

## 🏆 60-Second Hackathon Winning Demo
See [DEMO_FLOW_60S.md](DEMO_FLOW_60S.md) for the theatrical script, visual cues, and presenter voiceover to win judges in 1 minute.

---

## 🪝 Pre and Post Hooks

### 1. Git Workflow Hooks (`.githooks/`)
Version-controlled Git hooks ensure zero-leak security and prevent breaking commits:
* **`pre-commit`**: Scans staged files for unredacted credentials (Stripe live keys, JWTs, private keys) and verifies Python syntax across all modified files before allowing a commit.
* **`post-commit`**: Logs commit hash summary and reminds developers of pre-push test gating.
* **`pre-push`**: Automatically spins up the container test suite (`pytest tests/`) to ensure all deduplication and sanitization tests pass before pushing code to GitHub.

To enable them on any clone:
```bash
./scripts/setup-hooks.sh
# Sets git config core.hooksPath .githooks
```

### 2. Application Extensibility Hooks (`backend/app/engine/hooks.py`)
Allows teams to inject custom logic into the analysis pipeline:
* **`PreIngestHook`**: Inspects, enriches, or drops raw log payloads before clustering (e.g., token authentication, tenant tagging).
* **`PostIncidentHook`**: Executes automated remediation actions upon incident creation (e.g., triggering `kubectl rollout undo` webhooks, opening Jira tickets).

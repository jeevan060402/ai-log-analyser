# 🏆 Best Coding Practices & Engineering Standards

This document outlines the architectural patterns, security standards, and engineering best practices implemented throughout the **Universal AI Log Analyser & Intelligent Alerting Platform**.

---

## 1. Architectural Separation of Concerns (Clean Architecture)

The codebase strictly enforces unidirectional dependencies between layers:

```
[ Ingestion Layer: HTTP / CLI / Webhook ]
                  │
                  ▼
[ Core Sanitization: LogRedactor & LogParser ] (Pure Python, Zero External Deps)
                  │
                  ▼
[ Engine Layer: DrainMiner, IncidentManager, Evaluator ] (State Machine & Logic)
                  │
                  ▼
[ Dispatchers & AI Layer: SlackBlockKit, GeminiTriage ] (External I/O & Sinks)
```

- **`app/core/`**: Zero framework dependencies. Contains pure data sanitizers and parsers that can be unit-tested without mock servers or network calls.
- **`app/engine/`**: Manages state, algorithms, clustering, and deduplication. Does not depend on FastAPI.
- **`app/api/`**: Thin transport layer responsible solely for HTTP request decoding, status codes, and routing to the engine.

---

## 2. Asynchronous Concurrency & Resilience

### Bounded Queues for Backpressure Management
- **Problem**: When a server encounters an outage, 10,000 logs arrive per second. Spawning unconstrained tasks (`asyncio.create_task` per log) exhausts system memory.
- **Best Practice**: The event bus uses a **strictly bounded queue**:
  ```python
  queue = asyncio.Queue(maxsize=10_000)
  ```
  If incoming volume exceeds capacity, `put_nowait()` raises `QueueFull` allowing controlled drop or throttling without crashing the process.

### Graceful Lifecycle Management
- Background workers (`alert_worker` and `resolution_reaper`) are initialized inside FastAPI's `@asynccontextmanager lifespan(app)`:
  ```python
  yield  # App runs here
  # On SIGTERM / shutdown:
  worker_task.cancel()
  reaper_task.cancel()
  ```
  This guarantees that in-flight alerts complete before process termination.

### Thread Safety on In-Memory State
- Concurrent log bursts mutate shared incident state using an explicit asynchronous mutex (`asyncio.Lock`):
  ```python
  async with self._lock:
      incident = self._incidents.get(fingerprint)
      incident.occurrence_count += int(event.metric_value)
  ```

---

## 3. Security & Data Privacy (Zero-Leak Principle)

### Sanitization Prior to Ingestion & Reasoning
- Raw production logs often leak PII, JWT tokens, Stripe keys, passwords, and IP addresses.
- Logs pass through `LogRedactor.sanitize()` **before** entering the template clustering tree, vector store, or any LLM prompt:
  ```python
  sanitized = redactor.sanitize(raw_log)
  cluster, is_new = drain_miner.match_or_create(sanitized)
  ```

### Regex Precedence Hierarchy
- Specific token rules (`STRIPE_KEY`, `JWT_TOKEN`) execute before generic catch-all patterns (`GENERIC_KEY`), preventing misclassification and preserving log structure.

### Git Secret Leak Prevention
- Pre-commit hooks (`.githooks/pre-commit`) inspect staged diffs and abort commits if raw private keys or live API tokens are detected.

---

## 4. Deterministic Testing & Quality Gating

1. **Self-Contained Tests**: Unit tests require zero external databases, Redis queues, or live internet connections.
2. **Universal Test Compatibility**: Async tests are wrapped in synchronous runners so they execute seamlessly with or without third-party pytest plugins:
   ```python
   def test_deduplication():
       asyncio.run(_async_test_deduplication())
   ```
3. **CI/CD Integration**: `.github/workflows/ci.yml` runs automated regression tests and `ruff` lint checks on every pull request.

---

## 5. Extensibility via Declarative Configuration

- Rather than hardcoding domain rules in Python, project-specific behavior is decoupled into `alert_config.yaml`:
  - Regex patterns for benign errors.
  - Scheduled maintenance blackout windows.
  - Dynamic severity classification rules.
  - Target webhook routing.

# 🏛️ SOLID Principles Implementation Guide

This document provides a technical audit and architectural breakdown of how the **Universal AI Log Analyser & Intelligent Alerting Platform** strictly implements all five **SOLID Object-Oriented Design Principles**.

---

## 1. Single Responsibility Principle (SRP)
> *"A class or module should have one, and only one, reason to change."*

Every component in `backend/app/` is isolated to a single responsibility:

| Component | File Path | Single Responsibility | What It Does NOT Do |
| :--- | :--- | :--- | :--- |
| **`LogRedactor`** | `app/core/redactor.py` | Scrubbing PII, tokens, and credentials via regex. | Does not parse formats or evaluate alerts. |
| **`LogParser`** | `app/core/parser.py` | Normalizing unstructured strings into typed dictionaries. | Does not redact secrets or cluster logs. |
| **`DrainTemplateMiner`** | `app/engine/drain_miner.py` | Tree-based log template clustering and invariant extraction. | Does not manage incident states or send HTTP requests. |
| **`AlertEvaluator`** | `app/engine/evaluator.py` | Matching `AnomalyEvent` payloads against active `AlertRule` definitions. | Does not track deduplication or dispatch messages. |
| **`IncidentManager`** | `app/engine/manager.py` | Maintaining the incident lifecycle state machine, deduplication hashing, and silence reaper. | Does not format Slack blocks or make LLM calls. |
| **`AITriageSynthesizer`** | `app/engine/ai_triage.py` | LLM prompt engineering, root cause synthesis, and blast radius calculation. | Does not store logs or manage socket connections. |

---

## 2. Open/Closed Principle (OCP)
> *"Software entities should be open for extension, but closed for modification."*

The architecture allows adding new sinks, rules, and behaviors without touching existing, tested core classes:

### A. Pluggable Notification Channels
To add a new notification sink (e.g., Discord, PagerDuty, or Microsoft Teams), you subclass `NotificationChannel` and register it. No modifications to `IncidentManager` or `NotificationDispatcher` are required:

```python
class DiscordWebhookDispatcher(NotificationChannel):
    async def send_alert(self, incident: IncidentState, rule: AlertRule) -> bool:
        # Custom Discord embed formatting here
        return True

    async def send_resolution(self, incident: IncidentState) -> bool:
        return True

# Extension without modifying core code:
dispatcher.register_channel("discord", DiscordWebhookDispatcher(webhook_url))
```

### B. Declarative Project Profiles (`alert_config.yaml`)
Domain-specific behaviors (benign error regexes, blackout windows, escalation policies) are configured via declarative YAML, keeping the Python engine closed for modification while infinitely open for domain tuning.

---

## 3. Liskov Substitution Principle (LSP)
> *"Subtypes must be substitutable for their base types without altering program correctness."*

All notification sinks inherit from the abstract base class `NotificationChannel`:

```python
class NotificationChannel(abc.ABC):
    @abc.abstractmethod
    async def send_alert(self, incident: IncidentState, rule: AlertRule) -> bool:
        pass

    @abc.abstractmethod
    async def send_resolution(self, incident: IncidentState) -> bool:
        pass
```

- Both `MockLocalDispatcher` and `SlackWebhookDispatcher` conform identically to this contract:
  - Return types are strictly `bool`.
  - Signature expectations are identical.
  - Raising unhandled exceptions is prohibited; errors are encapsulated within the channel implementation.
- `NotificationDispatcher` can iterate through any collection of `NotificationChannel` instances without knowing their concrete implementation details.

---

## 4. Interface Segregation Principle (ISP)
> *"Clients should not be forced to depend on interfaces they do not use."*

Instead of a bloated "God Interface" (`ILogSystem` with 25 methods for parsing, redacting, clustering, alerting, and persisting), interfaces are decoupled into narrow, focused protocols:

- **`NotificationChannel`**: Exposes only `send_alert()` and `send_resolution()`.
- **`PreIngestHook`**: Only exposes `(dict) -> Optional[dict]`.
- **`PostIncidentHook`**: Only exposes `(dict) -> None`.

A custom team building an internal Slack bot only implements `NotificationChannel` without being forced to implement storage or parsing methods.

---

## 5. Dependency Inversion Principle (DIP)
> *"High-level modules should not depend on low-level modules. Both should depend on abstractions."*

### A. Decoupled Incident Manager
`IncidentManager` (high-level orchestration) does not instantiate or directly depend on `SlackWebhookDispatcher` (low-level network I/O). Instead, dependencies are injected via constructor:

```python
class IncidentManager:
    def __init__(
        self, 
        dispatcher: NotificationDispatcher,          # Injected abstraction
        ai_triage: Optional[AITriageSynthesizer] = None  # Injected abstraction
    ):
        self.dispatcher = dispatcher
        self.ai_triage = ai_triage or AITriageSynthesizer()
```

### B. Testing Without External Dependencies
Because dependencies are inverted and injected, unit tests instantiate `IncidentManager` with `MockLocalDispatcher`, enabling instantaneous, deterministic testing without needing active network interfaces or Slack tokens.

# ⚡ AI Log Analyser: Alerting Workbench & Project Tuning Specification

> **Platform Extensibility & Developer Experience Architecture**  
> Designed for high-scale observability, real-time cascade storm suppression, and sub-5-second root cause diagnosis.

---

## 📑 Table of Contents
1. [Executive Summary & Architectural Vision](#1-executive-summary--architectural-vision)
2. [Tunable Project Profile Schema (`alert_config.yaml` / JSON Schema)](#2-tunable-project-profile-schema)
   - [Schema Definition (`alert_config.schema.json`)](#schema-definition)
   - [Production-Grade Configuration (`alert_config.example.yaml`)](#production-grade-configuration)
   - [Routing, Escalation, & Suppression Rules Breakdown](#routing-escalation--suppression-rules)
3. [Developer UI / Workbench Experience](#3-developer-ui--workbench-experience)
   - [Workbench Information Architecture & Layout](#workbench-information-architecture)
   - [Status Badges & Occurrence Frequency Charts](#status-badges--frequency-charts)
   - [Instant Alert Preview Modal (Slack Block Kit & Discord Embeds)](#instant-alert-preview-modal)
   - [Cascade Failure Simulator & Live Ingress Chamber](#cascade-failure-simulator)
4. [TypeScript Contract Types (`types.ts`)](#4-typescript-contract-types)
5. [React Component Implementation (`WorkbenchComponents.tsx`)](#5-react-component-implementation)
6. [🏆 Hackathon Winning Demo Flow (60-Second Playbook)](#6-hackathon-winning-demo-flow)

---

## 1. Executive Summary & Architectural Vision

Legacy observability platforms fail during severe outages because of **Alert Storms**: a single upstream failure (e.g., database connection pool exhaustion or redis OOM) triggers a cascading domino effect across dozens of microservices. Within seconds, engineers receive thousands of duplicate, fragmented alerts, drowning out the actual root cause.

The **AI Log Analyser Alerting Workbench** solves this with a 3-layer architecture:

```mermaid
flowchart TD
    subgraph Ingress ["Log Stream Ingress (Up to 10k logs/sec)"]
        L1[checkout-db: FATAL max connections]
        L2[checkout-api: 504 Gateway Timeout x1200]
        L3[cart-svc: Redis ECONNREFUSED x800]
        L4[payment-gw: Upstream 502 x2800]
    end

    subgraph SuppressionEngine ["Layer 1: Project Tuning & Suppression Engine"]
        Maint[Maintenance Window Check]
        Benign[Known Benign Error Regex Filter]
        Dedup[Sliding Window Semantic Clustering (60s)]
        RateLimit[Token-Bucket Rate Limiting]
    end

    subgraph AIEngine ["Layer 2: Gemini 2.0 Flash Diagnostic Synthesis"]
        GraphTrace[Distributed Dependency Graph Reconstruction]
        RootCause[Root Cause Query & Commit Isolation]
        BlastCalc[Blast Radius & Impacted Users Estimation]
        RunbookAttach[Runbook & Rollback Command Association]
    end

    subgraph Dispatch ["Layer 3: Single Crisp Dispatch"]
        SlackCard["🚨 Exactly 1 Synthesized Slack Block Kit Alert"]
        DiscordCard["Discord Embed Notification"]
        PD["PagerDuty Incident (Auto-Escalation)"]
    end

    Ingress --> SuppressionEngine
    SuppressionEngine -->|4,820 logs suppressed / 99.98% noise reduction| AIEngine
    AIEngine --> Dispatch
```

---

## 2. Tunable Project Profile Schema

The project tuning configuration is governed by `alert_config.yaml`, validated strictly by `alert_config.schema.json`.

### Schema Definition (`alert_config.schema.json`)
The schema enforces strong typing, regex constraints, and structured validation for routing, maintenance windows, benign noise patterns, and AI triage parameters:

- **Validation Standard**: JSON Schema Draft-07.
- **Root Fields**: `version`, `project_id`, `display_name`, `owner_team`, `environment`, `ai_triage`, `suppression_rules`, `severity_rules`, `routing_rules`, `escalation_policies`, `channels`.
- **Reference**: Located in [`/Users/jeevan/.gemini/antigravity/scratch/alerting-workbench/alert_config.schema.json`](file:///Users/jeevan/.gemini/antigravity/scratch/alerting-workbench/alert_config.schema.json).

### Production-Grade Configuration (`alert_config.example.yaml`)

```yaml
version: "v1"
project_id: "checkout-payments-prod"
display_name: "Payments & Checkout Gateway (Production)"
owner_team: "core-payments-infra"
environment: "production"

# AI Triage & Clustering Settings
ai_triage:
  enabled: true
  model: "gemini-2.0-flash"
  confidence_threshold: 0.85           # Auto-label root cause & fire high-sev only if >= 85%
  grouping_window_seconds: 60          # 60-second window to group cascade logs
  max_cascade_wait_seconds: 180        # Hard ceiling before dispatching intermediate alert
  auto_root_cause_analysis: true
  blast_radius_detection: true
  remediation_suggestions: true
  mask_pii_before_llm: true            # Redact credit cards, emails, and tokens

# Suppression & Noise-Dampening Rules
suppression_rules:
  maintenance_windows:
    - id: "maint-weekly-db-reindex"
      name: "Weekly Aurora PostgreSQL VACUUM & Reindex"
      cron_schedule: "0 2 * * SUN"
      duration_minutes: 90
      timezone: "UTC"
      services_affected: ["checkout-db", "ledger-service"]
      action: "ARCHIVE_WITHOUT_NOTIFY"

    - id: "maint-q3-major-upgrade"
      name: "Payment Gateway v3.4 Cutover Migration"
      start_time: "2026-10-01T01:00:00Z"
      end_time: "2026-10-01T04:00:00Z"
      services_affected: ["*"]
      action: "DIGEST_SUMMARY_ON_COMPLETION"

  benign_errors:
    - id: "benign-client-abort"
      name: "Client Disconnect / HTTP 499"
      reason: "Mobile clients disconnecting on cellular handoffs"
      pattern: "(ClientAbortException|ECONNRESET|BrokenPipeException)"
      match_field: "message"
      service: "*"
      max_burst_per_minute: 2500       # Safety limit: alert if massive spike
      jira_or_github_ref: "INFRA-1092"

    - id: "benign-k8s-kubelet-probe"
      name: "Legacy Kubelet Probe 404"
      pattern: "GET /healthz/legacy 404"
      match_field: "message"
      service: "api-gateway"
      expires_at: "2026-12-31T23:59:59Z"

  rate_limiting:
    max_alerts_per_channel_hour: 15
    burst_window_seconds: 300
    overflow_action: "SUPPRESS_AND_DIGEST"

  flapping_protection:
    enabled: true
    transition_threshold: 3
    evaluation_window_minutes: 15
    action: "EXTEND_RESOLVE_DELAY"

# Dynamic Severity Rules
severity_rules:
  - severity: "P0_CRITICAL"
    conditions:
      error_rate_per_min: 500
      impacted_services_count: 3
      ai_confidence_gt: 0.85
      log_levels: ["FATAL", "ERROR"]
      tags:
        tier: "tier-0-core"

  - severity: "P1_HIGH"
    conditions:
      error_rate_per_min: 100
      impacted_services_count: 1
      ai_confidence_gt: 0.80

# Routing & Channel Dispatch
routing_rules:
  - id: "route-critical-db-payments"
    description: "P0 payment outages and database pool crashes dispatch to War Room & PagerDuty"
    match:
      severities: ["P0_CRITICAL"]
      root_cause_categories:
        - "DATABASE_CONNECTION_EXHAUSTION"
        - "DATABASE_DEADLOCK"
        - "NETWORK_TIMEOUT_CASCADE"
      services:
        - "checkout-api"
        - "payment-gateway"
    channels:
      - "slack_war_room"
      - "pagerduty_sev0"
    template: "rich_ai_interactive"
    escalation_policy: "escalation-p0-payments"

# Escalation Policies
escalation_policies:
  - id: "escalation-p0-payments"
    name: "P0 Critical Payments Escalation Tier"
    steps:
      - wait_minutes: 0                # Immediate
        notify_channels: ["slack_war_room", "pagerduty_sev0"]
        mention_groups: ["@oncall-payments"]
      - wait_minutes: 10               # If unacknowledged for 10 min
        notify_channels: ["pagerduty_sev0", "slack_war_room"]
        elevate_severity_to: "P0_CRITICAL"
        mention_groups: ["@channel", "@payments-secondary-oncall"]
      - wait_minutes: 25               # If unacknowledged for 25 min
        notify_channels: ["slack_war_room"]
        mention_groups: ["@vp-engineering"]
    auto_resolve_timeout_minutes: 15

# Channel Destination Definitions
channels:
  slack_war_room:
    type: "slack"
    endpoint_secret_env: "SLACK_WAR_ROOM_WEBHOOK_URL"
    channel_name: "#war-room-checkout-sev0"
    ping_targets: ["@oncall-payments"]
    interactive_actions_enabled: true

  pagerduty_sev0:
    type: "pagerduty"
    endpoint_secret_env: "PAGERDUTY_SEV0_INTEGRATION_KEY"
    interactive_actions_enabled: true
```

---

## 3. Developer UI / Workbench Experience

### Workbench Information Architecture
The Alerting Workbench is structured for rapid cognitive intake during high-stress incidents:

1. **Top Navbar**: Project context, active schema sync badge, and high-visibility **`[⚡ Simulate Cascade Failure]`** CTA.
2. **Top Metrics Banner**:
   - **Active Incidents**: Live counter with pulsing status badge.
   - **Storm Suppression Ratio**: Real-time KPI (`99.98%`, 4,821 logs → 1 alert).
   - **Mean Time to Triage (MTTA)**: Sub-second to 4.2s benchmark.
   - **AI Diagnostic Accuracy**: Confidence score gauge.
3. **Log Volume & Cascade Anomaly Timeline**:
   - Time-bucketed bar chart displaying nominal traffic, cascade error spikes, and the exact cluster trigger point.
4. **Live Incident Feed & Filter Bar**:
   - Quick filters (`ALL`, `FIRING`, `SILENCED`, `RESOLVED`).
   - Incident cards detailing AI root cause, blast radius, error velocity, and action buttons.
5. **Instant Alert Preview Modal**:
   - Side-by-side WYSIWYG rendering of Slack Block Kit and Discord Embeds.
6. **Cascade Failure Simulation Chamber**:
   - Stress-testing tool that injects 4,800+ cascading errors and visually streams deduplication in real time.

---

### Instant Alert Preview Modal (Slack Block Kit Visual Design)

The Slack card is rendered with pixel-level fidelity matching Slack desktop and mobile clients:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  [AI] AI Log Analyser APP  12:42 PM   #war-room-checkout-sev0              │
│ ▌ 🚨 [P0 CRITICAL] PostgreSQL Connection Pool Exhaustion on primary-db-01    │
│ ▌                                                                           │
│ ▌ ┌───────────────────────────────────────────────────────────────────────┐ │
│ ▌ │ ✨ Gemini 2.0 Flash Root Cause Diagnosis (97% confidence)             │ │
│ ▌ │ Worker threads on checkout-api blocked on HikariCP pool acquisition   │ │
│ ▌ │ (30/30 leased for >12s). Upstream gateway threw 504 timeouts across  │ │
│ ▌ │ checkout, cart, and payment-gateway services. Correlated with        │ │
│ ▌ │ unindexed query introduced in migration v2.4.1.                       │ │
│ ▌ └───────────────────────────────────────────────────────────────────────┘ │
│ ▌                                                                           │
│ ▌ IMPACTED ENVIRONMENT: production (us-east-1)                              │
│ ▌ SUPPRESSED ERRORS: 4,821 logs collapsed into 1 alert (99.98% noise drop)  │
│ ▌ AFFECTED SERVICES: checkout-api, cart-svc, payment-gateway                │
│ ▌ ESTIMATED IMPACT: ~1,420 checkout attempts failing                        │
│ ▌                                                                           │
│ ▌ Root Cause Query Traced:                                                  │
│ ▌ ┌───────────────────────────────────────────────────────────────────────┐ │
│ ▌ │ SELECT * FROM orders WHERE customer_id = 'c_99812'                   │ │
│ ▌ │   ORDER BY created_at DESC;                                           │ │
│ ▌ │ -- [WARNING: Full sequential table scan on 24M unindexed rows]        │ │
│ ▌ └───────────────────────────────────────────────────────────────────────┘ │
│ ▌                                                                           │
│ ▌ [Acknowledge]  [Rollback Deploy v2.4.1]  [Mute 1 Hour]  [Open Workbench ↗]│
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. TypeScript Contract Types (`types.ts`)

Type definitions are stored in [`/Users/jeevan/.gemini/antigravity/scratch/alerting-workbench/types.ts`](file:///Users/jeevan/.gemini/antigravity/scratch/alerting-workbench/types.ts).

Key interfaces include:
- `SeverityLevel`: `'P0_CRITICAL' | 'P1_HIGH' | 'P2_MEDIUM' | 'P3_LOW' | 'P4_INFO'`
- `IncidentStatus`: `'FIRING' | 'SILENCED' | 'RESOLVED' | 'SUPPRESSED' | 'TRIAGING_AI'`
- `AITriageConfig`: Model selection, confidence thresholds, cascade sliding windows, PII masking.
- `IncidentAlert`: Incident payload containing `AIDiagnosisPayload`, `CorrelatedLogEvidence`, `stats` (dedup ratio, error velocity), and `escalation` tracking.

---

## 5. React Component Implementation (`WorkbenchComponents.tsx`)

A complete, production-ready React / Tailwind CSS implementation is located in:
[`/Users/jeevan/.gemini/antigravity/scratch/alerting-workbench/WorkbenchComponents.tsx`](file:///Users/jeevan/.gemini/antigravity/scratch/alerting-workbench/WorkbenchComponents.tsx).

Components included:
- `StatusBadge` & `SeverityBadge`
- `OccurrenceFrequencyChart`
- `IncidentFeedCard`
- `InstantAlertPreviewModal`
- `CascadeFailureSimulator`
- `AlertingWorkbench` (Root Application View)

---

## 6. 🏆 Hackathon Winning Demo Flow

Full presentation playbook located in [`/Users/jeevan/.gemini/antigravity/scratch/alerting-workbench/DEMO_FLOW_60S.md`](file:///Users/jeevan/.gemini/antigravity/scratch/alerting-workbench/DEMO_FLOW_60S.md).

### Chronological Runbook (60 Seconds)

```
00:00 - 00:10 ─── The Hook & Shared Pain
                 "Every on-call engineer has lived this 2 AM nightmare:
                  one DB pool maxes out, and your phone explodes with 4,800 alerts."

00:10 - 00:25 ─── The Cascade Injection
                 [CLICK: Simulate Cascade Failure]
                 Log Ingress surges to 4,821 logs/sec across 4 microservices.

00:25 - 00:40 ─── The Secret Sauce (AI De-noising)
                 4,820 duplicate stack traces suppressed (99.98% noise reduction).
                 Gemini 2.0 Flash traces dependency graph in 1.4 seconds.

00:40 - 00:55 ─── The Crisp Actionable Slack Alert
                 Instant Alert Preview Modal opens with Slack chime:
                 1 alert identifying the exact unindexed query, blast radius,
                 and providing a 1-click rollback button.

00:55 - 01:00 ─── The Punchline & Close
                 "From 4,800 screaming alerts to 1 actionable fix in under 5 seconds.
                  That is how the AI Log Analyser ends alert fatigue forever."
```

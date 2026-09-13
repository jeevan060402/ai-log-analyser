/**
 * AI Log Analyser: Alerting Workbench & Project Tuning Types
 */

export type SeverityLevel = 'P0_CRITICAL' | 'P1_HIGH' | 'P2_MEDIUM' | 'P3_LOW' | 'P4_INFO';
export type IncidentStatus = 'FIRING' | 'SILENCED' | 'RESOLVED' | 'SUPPRESSED' | 'TRIAGING_AI';

export type RootCauseCategory =
  | 'DATABASE_CONNECTION_EXHAUSTION'
  | 'DATABASE_DEADLOCK'
  | 'NETWORK_TIMEOUT_CASCADE'
  | 'OUT_OF_MEMORY'
  | 'AUTH_PROVIDER_OUTAGE'
  | 'RATE_LIMIT_EXCEEDED'
  | 'CONFIG_PARSING_ERROR'
  | 'DISK_SPACE_EXHAUSTION'
  | 'UPSTREAM_DEPENDENCY_5XX'
  | 'UNKNOWN_ANOMALY';

export interface AITriageConfig {
  enabled: boolean;
  model: 'gemini-2.0-flash' | 'gemini-1.5-pro' | 'claude-3-5-sonnet' | 'gpt-4o';
  confidence_threshold: number;
  grouping_window_seconds: number;
  max_cascade_wait_seconds: number;
  auto_root_cause_analysis: boolean;
  blast_radius_detection: boolean;
  remediation_suggestions: boolean;
  mask_pii_before_llm: boolean;
}

export interface MaintenanceWindow {
  id: string;
  name: string;
  cron_schedule?: string;
  duration_minutes?: number;
  start_time?: string;
  end_time?: string;
  timezone?: string;
  services_affected: string[];
  action: 'DROP_SILENTLY' | 'ARCHIVE_WITHOUT_NOTIFY' | 'DIGEST_SUMMARY_ON_COMPLETION';
}

export interface BenignErrorFilter {
  id: string;
  name: string;
  reason: string;
  pattern: string;
  match_field: 'message' | 'stack_trace' | 'logger_name' | 'error_code' | 'any';
  service?: string;
  max_burst_per_minute?: number;
  expires_at?: string;
  jira_or_github_ref?: string;
}

export interface RateLimitingConfig {
  max_alerts_per_channel_hour: number;
  burst_window_seconds: number;
  overflow_action: 'SUPPRESS_AND_DIGEST' | 'DROP_LOW_PRIORITY';
}

export interface FlappingProtectionConfig {
  enabled: boolean;
  transition_threshold: number;
  evaluation_window_minutes: number;
  action: 'LOCK_FIRING_UNTIL_MANUAL_RESET' | 'EXTEND_RESOLVE_DELAY';
}

export interface SuppressionRules {
  maintenance_windows?: MaintenanceWindow[];
  benign_errors?: BenignErrorFilter[];
  rate_limiting?: RateLimitingConfig;
  flapping_protection?: FlappingProtectionConfig;
}

export interface SeverityRule {
  severity: SeverityLevel;
  conditions: {
    error_rate_per_min?: number;
    log_levels?: string[];
    impacted_services_count?: number;
    ai_confidence_gt?: number;
    has_stack_trace?: boolean;
    tags?: Record<string, string>;
  };
}

export interface RoutingRule {
  id: string;
  description?: string;
  match: {
    severities?: SeverityLevel[];
    services?: string[];
    environments?: string[];
    root_cause_categories?: RootCauseCategory[];
  };
  channels: string[];
  template?: 'rich_ai_interactive' | 'slack_compact' | 'pagerduty_brief' | 'json_raw';
  escalation_policy?: string;
}

export interface EscalationStep {
  wait_minutes: number;
  notify_channels: string[];
  elevate_severity_to?: SeverityLevel;
  mention_groups?: string[];
}

export interface EscalationPolicy {
  id: string;
  name: string;
  steps: EscalationStep[];
  auto_resolve_timeout_minutes: number;
}

export interface ChannelConfig {
  type: 'slack' | 'discord' | 'pagerduty' | 'opsgenie' | 'webhook' | 'email';
  endpoint_secret_env?: string;
  channel_name?: string;
  ping_targets?: string[];
  interactive_actions_enabled?: boolean;
}

export interface AlertProjectConfig {
  version: string;
  project_id: string;
  display_name: string;
  owner_team: string;
  environment: 'production' | 'staging' | 'development' | 'canary' | 'all';
  ai_triage: AITriageConfig;
  suppression_rules?: SuppressionRules;
  severity_rules?: SeverityRule[];
  routing_rules: RoutingRule[];
  escalation_policies?: EscalationPolicy[];
  channels?: Record<string, ChannelConfig>;
}

// ==============================================================================
// RUNTIME INCIDENT & WORKBENCH FEED MODELS
// ==============================================================================

export interface CorrelatedLogEvidence {
  timestamp: string;
  service: string;
  level: 'FATAL' | 'ERROR' | 'WARN';
  message: string;
  traceId: string;
  spanId?: string;
}

export interface AIDiagnosisPayload {
  summary: string;
  confidence: number;
  probableRootCause: string;
  category: RootCauseCategory;
  evidenceLogs: CorrelatedLogEvidence[];
  blastRadius: {
    impactedServices: string[];
    estimatedUsersAffected: number;
    failureRatePercent: number;
  };
  suggestedRunbook: {
    title: string;
    runbookUrl: string;
    executableCommand?: string;
    rollbackAvailable: boolean;
  };
}

export interface IncidentAlert {
  id: string;
  projectId: string;
  title: string;
  status: IncidentStatus;
  severity: SeverityLevel;
  timestamp: string;
  aiDiagnosis: AIDiagnosisPayload;
  stats: {
    rawLogsReceived: number;
    duplicateErrorsSuppressed: number;
    noiseReductionPercentage: number;
    errorVelocityPerSec: number;
    timeToIdentifyMs: number;
  };
  silenceInfo?: {
    silencedBy: string;
    silencedUntil: string;
    reason: string;
  };
  escalation: {
    policyId: string;
    currentStep: number;
    acknowledged: boolean;
    acknowledgedBy?: string;
    nextEscalationAt?: string;
  };
}

export interface CascadeSimulationScenario {
  id: string;
  name: string;
  description: string;
  rawLogFloodCount: number;
  propagationTimeSeconds: number;
  affectedMicroservices: string[];
  simulatedRootCause: RootCauseCategory;
}

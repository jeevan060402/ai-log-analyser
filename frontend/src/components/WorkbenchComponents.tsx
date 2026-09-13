import React, { useState } from "react";
import { 
  AlertTriangle, CheckCircle2, BellOff, Zap, Shield, Filter, 
  Play, RefreshCw, ExternalLink, Slack, MessageSquare, Terminal, 
  ChevronRight, ArrowUpRight, Activity, Layers, Clock, Cpu
} from "lucide-react";
import { IncidentAlert, SeverityLevel, IncidentStatus, AlertProjectConfig } from "./types";

// ==============================================================================
// 1. STATUS BADGES & SEVERITY CHIPS
// ==============================================================================

export const StatusBadge: React.FC<{ status: IncidentStatus; duration?: string }> = ({ status, duration }) => {
  switch (status) {
    case "FIRING":
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/30 animate-pulse">
          <span className="w-2 h-2 rounded-full bg-rose-500 shadow-sm shadow-rose-500/80 animate-ping" />
          FIRING {duration ? `(${duration})` : ""}
        </span>
      );
    case "SILENCED":
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-zinc-800 text-zinc-400 border border-zinc-700">
          <BellOff className="w-3 h-3 text-zinc-400" />
          SILENCED
        </span>
      );
    case "RESOLVED":
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
          <CheckCircle2 className="w-3 h-3 text-emerald-400" />
          RESOLVED
        </span>
      );
    case "SUPPRESSED":
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-500/10 text-amber-300 border border-amber-500/30">
          <Shield className="w-3 h-3 text-amber-400" />
          BENIGN SUPPRESSED
        </span>
      );
    case "TRIAGING_AI":
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-indigo-500/10 text-indigo-400 border border-indigo-500/30 animate-pulse">
          <Cpu className="w-3 h-3 text-indigo-400 animate-spin" />
          AI SYNTHESIZING
        </span>
      );
  }
};

export const SeverityBadge: React.FC<{ severity: SeverityLevel }> = ({ severity }) => {
  const styles: Record<SeverityLevel, { bg: string; text: string; border: string }> = {
    P0_CRITICAL: { bg: "bg-red-950/80", text: "text-red-300", border: "border-red-600" },
    P1_HIGH: { bg: "bg-orange-950/80", text: "text-orange-300", border: "border-orange-600" },
    P2_MEDIUM: { bg: "bg-amber-950/70", text: "text-amber-300", border: "border-amber-600" },
    P3_LOW: { bg: "bg-blue-950/60", text: "text-blue-300", border: "border-blue-700" },
    P4_INFO: { bg: "bg-zinc-900", text: "text-zinc-400", border: "border-zinc-700" }
  };
  const s = styles[severity] || styles.P4_INFO;
  return (
    <span className={`px-2 py-0.5 rounded text-[11px] font-mono font-bold tracking-wide uppercase border ${s.bg} ${s.text} ${s.border}`}>
      {severity.replace("_", " ")}
    </span>
  );
};

// ==============================================================================
// 2. FREQUENCY & ANOMALY CHART (SPARKLINE / HISTOGRAM)
// ==============================================================================

export const OccurrenceFrequencyChart: React.FC<{
  data: Array<{ time: string; normalCount: number; errorCount: number; isIncidentWindow?: boolean }>;
}> = ({ data }) => {
  const maxVal = Math.max(...data.map(d => d.normalCount + d.errorCount), 100);

  return (
    <div className="bg-zinc-900/90 border border-zinc-800 rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-rose-400" />
          <h4 className="text-sm font-semibold text-zinc-200">Log Volume & Cascade Anomaly Timeline</h4>
          <span className="text-xs text-zinc-500 font-mono">Last 30 minutes (1m buckets)</span>
        </div>
        <div className="flex items-center gap-4 text-xs font-mono">
          <span className="flex items-center gap-1.5 text-zinc-400">
            <span className="w-2.5 h-2.5 rounded-sm bg-zinc-600" /> Nominal Traffic
          </span>
          <span className="flex items-center gap-1.5 text-rose-400">
            <span className="w-2.5 h-2.5 rounded-sm bg-rose-500" /> Cascade Error Storm
          </span>
          <span className="flex items-center gap-1.5 text-indigo-400">
            <span className="w-2.5 h-2.5 rounded-sm bg-indigo-500/80" /> AI Cluster Fired
          </span>
        </div>
      </div>

      <div className="h-20 flex items-end gap-1 pt-2">
        {data.map((point, idx) => {
          const total = point.normalCount + point.errorCount;
          const heightPercent = Math.min(100, Math.round((total / maxVal) * 100));
          const errorRatio = point.errorCount / (total || 1);

          return (
            <div key={idx} className="flex-1 flex flex-col items-center h-full justify-end group relative">
              {point.isIncidentWindow && (
                <div className="absolute -top-3 w-1.5 h-1.5 rounded-full bg-rose-500 animate-ping" />
              )}
              <div
                style={{ height: `${heightPercent}%` }}
                className={`w-full rounded-t-sm transition-all duration-300 ${
                  point.isIncidentWindow
                    ? "bg-gradient-to-t from-rose-700 to-rose-400 shadow-sm shadow-rose-500/50"
                    : errorRatio > 0.3
                    ? "bg-amber-500/70"
                    : "bg-zinc-700/60 group-hover:bg-zinc-600"
                }`}
              />
              <div className="opacity-0 group-hover:opacity-100 pointer-events-none absolute -bottom-8 bg-zinc-950 text-[10px] font-mono text-zinc-300 px-2 py-1 rounded shadow-lg border border-zinc-800 z-20 whitespace-nowrap">
                {point.time} • Errors: {point.errorCount} | Traffic: {point.normalCount}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// ==============================================================================
// 3. INCIDENT CARD IN LIVE FEED
// ==============================================================================

export const IncidentFeedCard: React.FC<{
  incident: IncidentAlert;
  onOpenPreview: (incident: IncidentAlert) => void;
  onOpenRemediation: (incident: IncidentAlert) => void;
}> = ({ incident, onOpenPreview, onOpenRemediation }) => {
  return (
    <div className={`p-4 rounded-xl border transition-all ${
      incident.status === "FIRING"
        ? "bg-zinc-900/90 border-rose-500/40 shadow-lg shadow-rose-950/20 hover:border-rose-500/60"
        : "bg-zinc-900/50 border-zinc-800/80 hover:border-zinc-700"
    }`}>
      {/* Header Row */}
      <div className="flex items-start justify-between gap-3 mb-2.5">
        <div className="flex items-center gap-2 flex-wrap">
          <SeverityBadge severity={incident.severity} />
          <StatusBadge status={incident.status} duration="3m ago" />
          <h3 className="text-base font-semibold text-zinc-100 tracking-tight">
            {incident.title}
          </h3>
        </div>
        <div className="text-xs text-zinc-500 font-mono whitespace-nowrap">
          {incident.id}
        </div>
      </div>

      {/* AI Diagnosis Snippet */}
      <div className="p-3 rounded-lg bg-indigo-950/20 border border-indigo-500/20 mb-3">
        <div className="flex items-center justify-between text-xs mb-1">
          <span className="flex items-center gap-1.5 font-semibold text-indigo-300">
            <Cpu className="w-3.5 h-3.5 text-indigo-400" />
            Gemini 2.0 Synthesis • {(incident.aiDiagnosis.confidence * 100).toFixed(0)}% Confidence
          </span>
          <span className="text-[11px] font-mono text-indigo-400/80">
            Category: {incident.aiDiagnosis.category}
          </span>
        </div>
        <p className="text-xs text-zinc-300 leading-relaxed">
          {incident.aiDiagnosis.summary}
        </p>
      </div>

      {/* Metrics & Blast Radius Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-3 text-xs">
        <div className="bg-zinc-800/50 border border-zinc-800 rounded-md p-2">
          <span className="text-zinc-500 block text-[10px] uppercase font-mono">Deduplication</span>
          <span className="font-bold text-emerald-400 font-mono">
            {incident.stats.noiseReductionPercentage}%
          </span>
          <span className="text-zinc-500 text-[10px] ml-1 font-mono">
            ({incident.stats.rawLogsReceived} → 1)
          </span>
        </div>

        <div className="bg-zinc-800/50 border border-zinc-800 rounded-md p-2">
          <span className="text-zinc-500 block text-[10px] uppercase font-mono">Blast Radius</span>
          <span className="font-bold text-rose-400 font-mono">
            {incident.aiDiagnosis.blastRadius.impactedServices.length} services
          </span>
          <span className="text-zinc-500 text-[10px] ml-1 font-mono">
            (~{incident.aiDiagnosis.blastRadius.estimatedUsersAffected} users)
          </span>
        </div>

        <div className="bg-zinc-800/50 border border-zinc-800 rounded-md p-2">
          <span className="text-zinc-500 block text-[10px] uppercase font-mono">Error Velocity</span>
          <span className="font-bold text-amber-400 font-mono">
            {incident.stats.errorVelocityPerSec} / sec
          </span>
        </div>

        <div className="bg-zinc-800/50 border border-zinc-800 rounded-md p-2">
          <span className="text-zinc-500 block text-[10px] uppercase font-mono">Next Escalation</span>
          <span className="font-bold text-zinc-300 font-mono">
            {incident.escalation.acknowledged ? "ACKED" : "In 6m 20s"}
          </span>
        </div>
      </div>

      {/* Affected Services Tags */}
      <div className="flex items-center gap-1.5 flex-wrap mb-3.5">
        <span className="text-[11px] text-zinc-500 font-mono">Services:</span>
        {incident.aiDiagnosis.blastRadius.impactedServices.map(svc => (
          <span key={svc} className="px-2 py-0.5 rounded bg-zinc-800 text-zinc-300 font-mono text-[11px] border border-zinc-700/60">
            {svc}
          </span>
        ))}
      </div>

      {/* Action Toolbar */}
      <div className="flex items-center justify-between pt-2.5 border-t border-zinc-800/80 gap-2 flex-wrap">
        <div className="flex items-center gap-2">
          <button
            onClick={() => onOpenPreview(incident)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-zinc-700 transition-colors"
          >
            <Slack className="w-3.5 h-3.5 text-pink-400" />
            Instant Alert Preview
          </button>

          <button
            onClick={() => onOpenRemediation(incident)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/40 transition-colors"
          >
            <Zap className="w-3.5 h-3.5 text-indigo-400" />
            Runbook Actions
          </button>
        </div>

        <div className="flex items-center gap-2">
          <button className="px-2.5 py-1.5 rounded-lg text-xs font-medium text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition-colors">
            Silence 1h
          </button>
          <button className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-sm shadow-emerald-700/40 transition-colors">
            Acknowledge
          </button>
        </div>
      </div>
    </div>
  );
};

// ==============================================================================
// 4. INSTANT ALERT PREVIEW MODAL (SLACK BLOCK KIT & DISCORD EMBED)
// ==============================================================================

export const InstantAlertPreviewModal: React.FC<{
  isOpen: boolean;
  incident: IncidentAlert;
  onClose: () => void;
}> = ({ isOpen, incident, onClose }) => {
  const [activeTab, setActiveTab] = useState<"slack" | "discord">("slack");

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-zinc-950 border border-zinc-800 rounded-2xl w-full max-w-4xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-zinc-800 flex items-center justify-between bg-zinc-900/60">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-indigo-600/20 border border-indigo-500/40 flex items-center justify-center text-indigo-400">
              <Slack className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-base font-bold text-zinc-100 flex items-center gap-2">
                Instant Alert Preview
                <span className="text-xs font-normal text-zinc-400 font-mono">WYSIWYG Dispatch Engine</span>
              </h3>
              <p className="text-xs text-zinc-500">
                Verified representation of synthesized incident payload across notification endpoints
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* View Switcher Tabs */}
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-0.5 flex items-center text-xs font-medium">
              <button
                onClick={() => setActiveTab("slack")}
                className={`px-3 py-1.5 rounded-md flex items-center gap-1.5 ${
                  activeTab === "slack" ? "bg-zinc-800 text-zinc-100 shadow-sm" : "text-zinc-400 hover:text-zinc-200"
                }`}
              >
                <Slack className="w-3.5 h-3.5 text-pink-400" /> Slack Block Kit
              </button>
              <button
                onClick={() => setActiveTab("discord")}
                className={`px-3 py-1.5 rounded-md flex items-center gap-1.5 ${
                  activeTab === "discord" ? "bg-zinc-800 text-zinc-100 shadow-sm" : "text-zinc-400 hover:text-zinc-200"
                }`}
              >
                <MessageSquare className="w-3.5 h-3.5 text-indigo-400" /> Discord Embed
              </button>
            </div>

            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 transition-colors"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-4 bg-zinc-950/90">
          {activeTab === "slack" && (
            <div className="max-w-2xl mx-auto font-sans bg-[#1A1D21] text-[#D1D2D3] border border-[#2C3136] rounded-xl p-4 shadow-xl">
              {/* Slack Bot Header */}
              <div className="flex items-center gap-2 mb-2">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-rose-500 to-indigo-600 flex items-center justify-center text-white font-bold text-xs shadow">
                  AI
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-white text-sm">AI Log Analyser</span>
                    <span className="bg-zinc-700/60 text-zinc-300 text-[10px] px-1 rounded uppercase font-semibold">APP</span>
                    <span className="text-xs text-zinc-400">12:42 PM</span>
                  </div>
                  <div className="text-[11px] text-zinc-400 font-mono">channel: #war-room-checkout-sev0</div>
                </div>
              </div>

              {/* Slack Card with Red Left Border */}
              <div className="border-l-4 border-rose-500 pl-3.5 py-1 space-y-3 bg-zinc-900/30 rounded-r-md">
                <div className="text-sm font-bold text-white flex items-center gap-1.5">
                  🚨 [P0 CRITICAL] PostgreSQL Connection Pool Exhaustion on primary-db-01
                </div>

                <div className="text-xs text-zinc-300 leading-relaxed bg-[#222529] p-3 rounded border border-zinc-700/60">
                  <div className="font-semibold text-indigo-300 flex items-center gap-1 mb-1">
                    ✨ Gemini 2.0 Flash Root Cause Diagnosis (97% confidence)
                  </div>
                  {incident.aiDiagnosis.summary}
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs font-mono bg-[#222529]/60 p-2.5 rounded border border-zinc-800">
                  <div>
                    <span className="text-zinc-400 block text-[10px]">IMPACTED ENVIRONMENT:</span>
                    <span className="text-zinc-200 font-bold">production (us-east-1)</span>
                  </div>
                  <div>
                    <span className="text-zinc-400 block text-[10px]">SUPPRESSED ERRORS:</span>
                    <span className="text-emerald-400 font-bold">4,821 logs collapsed into 1 alert</span>
                  </div>
                  <div>
                    <span className="text-zinc-400 block text-[10px]">AFFECTED SERVICES:</span>
                    <span className="text-rose-400 font-bold">checkout-api, cart-svc, payment-gw</span>
                  </div>
                  <div>
                    <span className="text-zinc-400 block text-[10px]">ESTIMATED IMPACT:</span>
                    <span className="text-amber-400 font-bold">~1,420 checkout attempts</span>
                  </div>
                </div>

                <div>
                  <div className="text-[11px] text-zinc-400 font-mono mb-1">Root Cause Query Traced:</div>
                  <pre className="bg-black/70 p-2 rounded text-[11px] font-mono text-emerald-300 overflow-x-auto border border-zinc-800">
SELECT * FROM orders WHERE customer_id = &apos;c_99812&apos; ORDER BY created_at DESC;
-- [WARNING: Full sequential scan on 24M unindexed rows]
                  </pre>
                </div>

                <div className="flex items-center gap-2 pt-1 flex-wrap">
                  <button className="px-3 py-1.5 bg-[#007A5A] hover:bg-[#148567] text-white text-xs font-bold rounded shadow-sm">
                    Acknowledge
                  </button>
                  <button className="px-3 py-1.5 bg-[#E01E5A] hover:bg-[#EC2D69] text-white text-xs font-bold rounded shadow-sm">
                    Rollback Deploy v2.4.1
                  </button>
                  <button className="px-3 py-1.5 bg-[#2C3136] hover:bg-[#383F45] text-zinc-200 text-xs font-medium rounded border border-zinc-600">
                    Mute 1 Hour
                  </button>
                  <button className="px-3 py-1.5 bg-[#2C3136] hover:bg-[#383F45] text-indigo-300 text-xs font-medium rounded border border-zinc-600 flex items-center gap-1">
                    Open Workbench <ExternalLink className="w-3 h-3" />
                  </button>
                </div>
              </div>
            </div>
          )}

          {activeTab === "discord" && (
            <div className="max-w-2xl mx-auto font-sans bg-[#313338] text-[#DBDEE1] rounded-xl p-4 shadow-xl border border-[#232428]">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-full bg-rose-600 flex items-center justify-center text-white font-black text-sm">
                  AI
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-bold text-white text-sm">AI Log Analyser Bot</span>
                    <span className="bg-[#5865F2] text-white text-[10px] px-1 rounded uppercase font-semibold">BOT</span>
                    <span className="text-xs text-zinc-400">Today at 12:42 PM</span>
                  </div>

                  <div className="border-l-4 border-[#ED4245] bg-[#2B2D31] p-4 rounded-r-lg space-y-3">
                    <div className="text-sm font-bold text-white">
                      🚨 [P0 CRITICAL] PostgreSQL Connection Pool Exhaustion
                    </div>
                    <p className="text-xs text-zinc-300">
                      {incident.aiDiagnosis.summary}
                    </p>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div>
                        <span className="text-zinc-400 block font-semibold">Services Affected</span>
                        <span className="text-zinc-200">checkout-api, cart-svc, payment-gw</span>
                      </div>
                      <div>
                        <span className="text-zinc-400 block font-semibold">Noise Suppressed</span>
                        <span className="text-emerald-400 font-bold">99.98% (4,821 logs → 1)</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 border-t border-zinc-800 bg-zinc-900/60 flex items-center justify-between text-xs text-zinc-400">
          <span>Config Rule: <code className="text-indigo-300 font-mono">route-critical-db-payments</code></span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 font-medium transition-colors"
          >
            Close Preview
          </button>
        </div>

      </div>
    </div>
  );
};

// ==============================================================================
// 5. CASCADE FAILURE SIMULATOR & TRIGGER DRAWER
// ==============================================================================

export const CascadeFailureSimulator: React.FC<{
  isOpen: boolean;
  onClose: () => void;
  onSimulationTriggered: (scenarioId: string) => void;
}> = ({ isOpen, onClose, onSimulationTriggered }) => {
  const [selectedScenario, setSelectedScenario] = useState("db-pool-exhaustion");
  const [simulating, setSimulating] = useState(false);
  const [logCount, setLogCount] = useState(0);
  const [step, setStep] = useState<number>(0);

  if (!isOpen) return null;

  const handleStartSimulation = () => {
    setSimulating(true);
    setLogCount(0);
    setStep(1);

    const interval = setInterval(() => {
      setLogCount(prev => {
        if (prev >= 4821) {
          clearInterval(interval);
          setStep(2);
          setTimeout(() => {
            setStep(3);
            setTimeout(() => {
              setStep(4);
              setSimulating(false);
              onSimulationTriggered(selectedScenario);
            }, 1000);
          }, 1200);
          return 4821;
        }
        return prev + Math.floor(Math.random() * 450) + 120;
      });
    }, 80);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-zinc-950 border border-zinc-800 rounded-2xl w-full max-w-2xl shadow-2xl overflow-hidden p-6 space-y-6">
        <div className="flex items-center justify-between border-b border-zinc-800 pb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-rose-400">
              <Zap className="w-5 h-5 animate-pulse" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-zinc-100">Cascade Failure Simulation Chamber</h3>
              <p className="text-xs text-zinc-400">Stress-test suppression rules & live AI root-cause deduplication</p>
            </div>
          </div>
          <button onClick={onClose} className="text-zinc-500 hover:text-zinc-200">✕</button>
        </div>

        <div className="space-y-3">
          <label className="text-xs font-semibold text-zinc-400 uppercase tracking-wider block">
            Select Cascade Scenario
          </label>
          <div className="grid grid-cols-1 gap-2">
            {[
              {
                id: "db-pool-exhaustion",
                title: "Aurora PostgreSQL Connection Pool Exhaustion",
                desc: "Simulates 5,000 cascading 504 gateway timeout errors across checkout, cart, and payment-gateway services.",
                vol: "4,821 logs in 4.2s",
                services: ["checkout-db", "checkout-api", "cart-svc", "payment-gateway"]
              },
              {
                id: "redis-oom",
                title: "Redis Cluster Memory Thrashing & Eviction Storm",
                desc: "Simulates mass token revocation and session invalidation cascade on auth endpoints.",
                vol: "2,600 logs in 3.1s",
                services: ["redis-l2", "auth-service", "api-gateway"]
              }
            ].map(sc => (
              <div
                key={sc.id}
                onClick={() => setSelectedScenario(sc.id)}
                className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
                  selectedScenario === sc.id
                    ? "bg-indigo-950/30 border-indigo-500/60 shadow-md shadow-indigo-950/40"
                    : "bg-zinc-900/40 border-zinc-800 hover:border-zinc-700"
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-semibold text-zinc-200">{sc.title}</span>
                  <span className="text-xs font-mono text-indigo-400 font-bold">{sc.vol}</span>
                </div>
                <p className="text-xs text-zinc-400 mb-2">{sc.desc}</p>
                <div className="flex gap-1.5 flex-wrap">
                  {sc.services.map(s => (
                    <span key={s} className="text-[10px] font-mono px-2 py-0.5 rounded bg-zinc-800 text-zinc-400">
                      {s}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        {simulating && (
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 space-y-3">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-zinc-400">Raw Log Ingress Stream:</span>
              <span className="text-rose-400 font-bold text-base">{logCount.toLocaleString()} logs</span>
            </div>
            
            <div className="h-2 bg-zinc-800 rounded-full overflow-hidden">
              <div
                style={{ width: `${Math.min(100, (logCount / 4821) * 100)}%` }}
                className="h-full bg-gradient-to-r from-rose-500 to-indigo-500 transition-all duration-75"
              />
            </div>

            <div className="text-xs font-mono space-y-1 pt-1">
              <div className={`flex items-center gap-2 ${step >= 1 ? "text-zinc-200" : "text-zinc-600"}`}>
                {step === 1 ? "⚡" : "✓"} Ingesting high-velocity cascade flood...
              </div>
              <div className={`flex items-center gap-2 ${step >= 2 ? "text-indigo-300" : "text-zinc-600"}`}>
                {step === 2 ? "🔄" : step > 2 ? "✓" : "○"} Running AI Semantic Fingerprint & De-noising (4,820 benign/duplicate logs suppressed)...
              </div>
              <div className={`flex items-center gap-2 ${step >= 3 ? "text-amber-300" : "text-zinc-600"}`}>
                {step === 3 ? "🔍" : step > 3 ? "✓" : "○"} Isolating root cause hypothesis via Gemini 2.0 Flash...
              </div>
              <div className={`flex items-center gap-2 ${step >= 4 ? "text-emerald-400 font-bold" : "text-zinc-600"}`}>
                {step >= 4 ? "🚀" : "○"} 1 Unified Actionable Alert Dispatched to Slack & PagerDuty!
              </div>
            </div>
          </div>
        )}

        <div className="flex items-center justify-end gap-3 pt-2">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-xs font-medium text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleStartSimulation}
            disabled={simulating}
            className="flex items-center gap-2 px-5 py-2 rounded-xl text-xs font-bold bg-rose-600 hover:bg-rose-500 text-white shadow-lg shadow-rose-700/30 transition-all disabled:opacity-50"
          >
            <Play className="w-4 h-4 fill-white" />
            {simulating ? "Injecting Cascade Failure..." : "Trigger Cascade Storm Test"}
          </button>
        </div>
      </div>
    </div>
  );
};

// ==============================================================================
// 6. MAIN ALERTING WORKBENCH CONTAINER COMPONENT
// ==============================================================================

const MOCK_INCIDENT: IncidentAlert = {
  id: "INC-88921",
  projectId: "checkout-payments-prod",
  title: "PostgreSQL Connection Pool Exhaustion on primary-db-01",
  status: "FIRING",
  severity: "P0_CRITICAL",
  timestamp: new Date().toISOString(),
  aiDiagnosis: {
    summary: "Worker threads on checkout-api blocked on db connection pool acquisition (30/30 leased for >12s). Upstream gateway threw 504 timeouts across checkout, cart, and payment-gateway services. Correlated with unindexed query introduced in migration v2.4.1.",
    confidence: 0.97,
    probableRootCause: "HikariCP pool starvation caused by unindexed ORDER BY on orders(created_at).",
    category: "DATABASE_CONNECTION_EXHAUSTION",
    evidenceLogs: [
      {
        timestamp: "2026-09-13T12:40:11.201Z",
        service: "checkout-db",
        level: "FATAL",
        message: "FATAL: remaining connection slots are reserved for non-replication superuser connections",
        traceId: "tr-99812-db"
      }
    ],
    blastRadius: {
      impactedServices: ["checkout-api", "cart-svc", "payment-gateway", "notification-worker"],
      estimatedUsersAffected: 1420,
      failureRatePercent: 88.4
    },
    suggestedRunbook: {
      title: "Scale HikariCP & Rollback Migration v2.4.1",
      runbookUrl: "https://runbooks.corp/checkout/db-pool-recovery",
      executableCommand: "kubectl rollout undo deployment/checkout-api -n prod",
      rollbackAvailable: true
    }
  },
  stats: {
    rawLogsReceived: 4821,
    duplicateErrorsSuppressed: 4820,
    noiseReductionPercentage: 99.98,
    errorVelocityPerSec: 320,
    timeToIdentifyMs: 4200
  },
  escalation: {
    policyId: "escalation-p0-payments",
    currentStep: 1,
    acknowledged: false,
    nextEscalationAt: "2026-09-13T12:55:00Z"
  }
};

const MOCK_CHART_DATA = [
  { time: "12:15", normalCount: 420, errorCount: 0 },
  { time: "12:18", normalCount: 480, errorCount: 1 },
  { time: "12:21", normalCount: 510, errorCount: 0 },
  { time: "12:24", normalCount: 490, errorCount: 2 },
  { time: "12:27", normalCount: 460, errorCount: 1 },
  { time: "12:30", normalCount: 530, errorCount: 0 },
  { time: "12:33", normalCount: 510, errorCount: 3 },
  { time: "12:36", normalCount: 590, errorCount: 8 },
  { time: "12:39", normalCount: 620, errorCount: 280, isIncidentWindow: true },
  { time: "12:40", normalCount: 650, errorCount: 1850, isIncidentWindow: true },
  { time: "12:41", normalCount: 710, errorCount: 2680, isIncidentWindow: true },
  { time: "12:42", normalCount: 680, errorCount: 940, isIncidentWindow: true }
];

export const AlertingWorkbench: React.FC = () => {
  const [incidents, setIncidents] = useState<IncidentAlert[]>([MOCK_INCIDENT]);
  const [selectedIncident, setSelectedIncident] = useState<IncidentAlert | null>(null);
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [isSimulatorOpen, setIsSimulatorOpen] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>("ALL");

  const handleOpenPreview = (inc: IncidentAlert) => {
    setSelectedIncident(inc);
    setIsPreviewOpen(true);
  };

  const handleSimulationTriggered = (scenarioId: string) => {
    setIsSimulatorOpen(false);
    // Add synthesized cascade alert
    const newAlert: IncidentAlert = {
      ...MOCK_INCIDENT,
      id: `INC-${Math.floor(10000 + Math.random() * 90000)}`,
      timestamp: new Date().toISOString(),
      stats: {
        rawLogsReceived: 4821,
        duplicateErrorsSuppressed: 4820,
        noiseReductionPercentage: 99.98,
        errorVelocityPerSec: 410,
        timeToIdentifyMs: 3800
      }
    };
    setIncidents(prev => [newAlert, ...prev]);
    setSelectedIncident(newAlert);
    setIsPreviewOpen(true);
  };

  return (
    <div className="min-h-screen bg-[#0E1117] text-zinc-100 p-6 font-sans">
      <div className="max-w-7xl mx-auto space-y-6">
        
        {/* Top Navbar */}
        <header className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-zinc-800">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-rose-500 via-indigo-600 to-cyan-400 p-[1px] shadow-lg shadow-indigo-950/50">
              <div className="w-full h-full bg-[#0E1117] rounded-[11px] flex items-center justify-center">
                <Activity className="w-5 h-5 text-rose-400" />
              </div>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-bold tracking-tight text-white">Alerting Workbench</h1>
                <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                  config: alert_config.yaml (Synced)
                </span>
              </div>
              <p className="text-xs text-zinc-400">
                Project: <span className="text-zinc-200 font-semibold">checkout-payments-prod</span> • AI Triage: <span className="text-indigo-400 font-semibold">Gemini 2.0 Flash</span>
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 w-full sm:w-auto">
            <button
              onClick={() => setIsSimulatorOpen(true)}
              className="flex-1 sm:flex-initial flex items-center justify-center gap-2 px-4 py-2 rounded-xl text-xs font-bold bg-gradient-to-r from-rose-600 to-indigo-600 hover:from-rose-500 hover:to-indigo-500 text-white shadow-lg shadow-rose-900/30 hover:shadow-rose-900/50 transition-all cursor-pointer"
            >
              <Zap className="w-4 h-4 fill-white" />
              ⚡ Simulate Cascade Failure
            </button>

            <button className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-medium bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-zinc-700 transition-colors">
              <Layers className="w-3.5 h-3.5 text-zinc-400" />
              Edit Schema
            </button>
          </div>
        </header>

        {/* Top KPI Metrics Banner */}
        <section className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <div className="bg-zinc-900/70 border border-zinc-800 rounded-xl p-4">
            <div className="flex items-center justify-between text-xs text-zinc-400 mb-1">
              <span>Active Alerts</span>
              <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping" />
            </div>
            <div className="text-2xl font-bold font-mono text-white flex items-baseline gap-2">
              1 <span className="text-xs font-normal text-rose-400">FIRING</span>
            </div>
            <div className="text-[11px] text-zinc-500 mt-1">2 Silenced • 18 Resolved (24h)</div>
          </div>

          <div className="bg-zinc-900/70 border border-zinc-800 rounded-xl p-4">
            <div className="flex items-center justify-between text-xs text-zinc-400 mb-1">
              <span>Storm Suppression Ratio</span>
              <Shield className="w-3.5 h-3.5 text-emerald-400" />
            </div>
            <div className="text-2xl font-bold font-mono text-emerald-400">
              99.98%
            </div>
            <div className="text-[11px] text-zinc-500 mt-1">4,821 storm logs collapsed → 1 incident</div>
          </div>

          <div className="bg-zinc-900/70 border border-zinc-800 rounded-xl p-4">
            <div className="flex items-center justify-between text-xs text-zinc-400 mb-1">
              <span>Mean Time to Triage (MTTA)</span>
              <Clock className="w-3.5 h-3.5 text-indigo-400" />
            </div>
            <div className="text-2xl font-bold font-mono text-indigo-300">
              4.2s
            </div>
            <div className="text-[11px] text-zinc-500 mt-1">Automated root cause isolation</div>
          </div>

          <div className="bg-zinc-900/70 border border-zinc-800 rounded-xl p-4">
            <div className="flex items-center justify-between text-xs text-zinc-400 mb-1">
              <span>AI Accuracy Confidence</span>
              <Cpu className="w-3.5 h-3.5 text-cyan-400" />
            </div>
            <div className="text-2xl font-bold font-mono text-cyan-300">
              97.2%
            </div>
            <div className="text-[11px] text-zinc-500 mt-1">Zero hallucinations across 50 tests</div>
          </div>
        </section>

        {/* Global Log Volume & Frequency Sparkline */}
        <section>
          <OccurrenceFrequencyChart data={MOCK_CHART_DATA} />
        </section>

        {/* Filter Bar & Feed */}
        <section className="space-y-4">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 bg-zinc-900/40 p-3 rounded-xl border border-zinc-800/80">
            <div className="flex items-center gap-1.5 flex-wrap text-xs">
              <span className="text-zinc-500 font-mono mr-1">Status:</span>
              {["ALL", "FIRING", "SILENCED", "RESOLVED"].map(st => (
                <button
                  key={st}
                  onClick={() => setStatusFilter(st)}
                  className={`px-3 py-1 rounded-lg font-medium transition-colors ${
                    statusFilter === st
                      ? "bg-zinc-800 text-white border border-zinc-700"
                      : "text-zinc-400 hover:text-zinc-200"
                  }`}
                >
                  {st} {st === "FIRING" ? "(1)" : st === "SILENCED" ? "(2)" : ""}
                </button>
              ))}
            </div>

            <div className="text-xs text-zinc-500 font-mono">
              Displaying 1 active cascade incident
            </div>
          </div>

          {/* Incident Feed List */}
          <div className="space-y-3">
            {incidents.map(inc => (
              <IncidentFeedCard
                key={inc.id}
                incident={inc}
                onOpenPreview={handleOpenPreview}
                onOpenRemediation={() => alert("Runbook: kubectl rollout undo deployment/checkout-api -n prod")}
              />
            ))}
          </div>
        </section>

        {/* Instant Alert Preview Modal */}
        {selectedIncident && (
          <InstantAlertPreviewModal
            isOpen={isPreviewOpen}
            incident={selectedIncident}
            onClose={() => setIsPreviewOpen(false)}
          />
        )}

        {/* Cascade Simulator Modal */}
        <CascadeFailureSimulator
          isOpen={isSimulatorOpen}
          onClose={() => setIsSimulatorOpen(false)}
          onSimulationTriggered={handleSimulationTriggered}
        />

      </div>
    </div>
  );
};

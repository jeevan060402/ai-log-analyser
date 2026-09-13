import React, { useState, useEffect } from "react";
import { 
  GitPullRequest, CheckCircle2, Copy, ExternalLink, 
  MessageSquare, Send, Sparkles, Terminal, X, AlertTriangle, ArrowRight
} from "lucide-react";

// ==============================================================================
// 1. REAL-TIME SERVER-SENT EVENTS (SSE) STREAM HOOK
// ==============================================================================
export interface StreamMessage {
  type: "LOG_SURGE" | "INCIDENT_UPDATED" | "CONNECTED";
  timestamp: string;
  data: any;
}

export function useAlertStream(apiUrl: string = "http://localhost:8000") {
  const [isConnected, setIsConnected] = useState(false);
  const [liveLogCount, setLiveLogCount] = useState(0);
  const [latestEvent, setLatestEvent] = useState<StreamMessage | null>(null);

  useEffect(() => {
    const eventSource = new EventSource(`${apiUrl}/api/v1/alerts/stream`);

    eventSource.onopen = () => setIsConnected(true);
    eventSource.onmessage = (event) => {
      try {
        const payload: StreamMessage = JSON.parse(event.data);
        setLatestEvent(payload);
        if (payload.type === "LOG_SURGE") {
          setLiveLogCount((prev) => prev + (payload.data.count || 1));
        }
      } catch (err) {
        console.error("SSE parse error", err);
      }
    };
    eventSource.onerror = () => setIsConnected(false);

    return () => eventSource.close();
  }, [apiUrl]);

  return { isConnected, liveLogCount, latestEvent };
}

// ==============================================================================
// 2. 1-CLICK GITHUB PULL REQUEST REMEDIATION MODAL
// ==============================================================================
export interface PullRequestModalProps {
  isOpen: boolean;
  onClose: () => void;
  incidentId: string;
  incidentTitle: string;
}

export const PullRequestModal: React.FC<PullRequestModalProps> = ({
  isOpen,
  onClose,
  incidentId,
  incidentTitle
}) => {
  const [loading, setLoading] = useState(false);
  const [prData, setPrData] = useState<any>(null);

  useEffect(() => {
    if (isOpen && !prData) {
      setLoading(true);
      fetch(`http://localhost:8000/api/v1/incidents/${incidentId}/create-pr`, { method: "POST" })
        .then((res) => res.json())
        .then((data) => {
          setPrData(data);
          setLoading(false);
        })
        .catch(() => setLoading(false));
    }
  }, [isOpen, incidentId]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div className="w-full max-w-3xl rounded-2xl border border-zinc-800 bg-zinc-950 p-6 shadow-2xl">
        <div className="flex items-center justify-between border-b border-zinc-800 pb-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/30">
              <GitPullRequest className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">Autonomous GitHub Pull Request</h2>
              <p className="text-xs text-zinc-400">Incident {incidentId}: {incidentTitle}</p>
            </div>
          </div>
          <button onClick={onClose} className="text-zinc-400 hover:text-white">
            <X className="h-5 w-5" />
          </button>
        </div>

        {loading ? (
          <div className="py-12 text-center text-zinc-400">
            <Sparkles className="mx-auto h-8 w-8 animate-spin text-purple-400 mb-3" />
            <p className="text-sm">Synthesizing verified unified git diff & opening branch...</p>
          </div>
        ) : prData ? (
          <div className="mt-4 space-y-4">
            <div className="flex items-center justify-between rounded-xl bg-emerald-500/10 border border-emerald-500/30 p-3">
              <div className="flex items-center gap-2 text-emerald-400 text-sm font-medium">
                <CheckCircle2 className="h-4 w-4" />
                <span>Pull Request Ready: <b>Branch {prData.branch}</b></span>
              </div>
              <a
                href={prData.pr_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-xs font-semibold bg-emerald-500 text-black px-3 py-1.5 rounded-lg hover:bg-emerald-400 transition"
              >
                View on GitHub <ExternalLink className="h-3 w-3" />
              </a>
            </div>

            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-zinc-400">Proposed Unified Git Diff</label>
              <pre className="mt-1 max-h-56 overflow-auto rounded-xl bg-zinc-900 border border-zinc-800 p-3 text-xs font-mono text-emerald-300">
                {prData.diff}
              </pre>
            </div>
          </div>
        ) : null}

        <div className="mt-6 flex justify-end">
          <button onClick={onClose} className="px-4 py-2 text-sm text-zinc-400 hover:text-white">
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

// ==============================================================================
// 3. INTERACTIVE "CHAT WITH LOGS" NATURAL LANGUAGE DRAWER
// ==============================================================================
export interface LogCopilotDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

export const LogCopilotDrawer: React.FC<LogCopilotDrawerProps> = ({ isOpen, onClose }) => {
  const [messages, setMessages] = useState<Array<{ sender: "user" | "copilot"; text: string; citations?: any[] }>>([
    {
      sender: "copilot",
      text: "👋 I'm your AI Log Copilot. Ask anything about recent error clusters, impacted customers, or failure root causes."
    }
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSend = async (queryText?: string) => {
    const q = queryText || input;
    if (!q.trim()) return;

    setMessages((prev) => [...prev, { sender: "user", text: q }]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch("http://localhost:8000/api/v1/copilot/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: q })
      });
      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        { sender: "copilot", text: data.answer, citations: data.citations }
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { sender: "copilot", text: "Error connecting to AI Copilot engine." }
      ]);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-full max-w-lg bg-zinc-950 border-l border-zinc-800 shadow-2xl flex flex-col">
      {/* Drawer Header */}
      <div className="flex items-center justify-between p-4 border-b border-zinc-800">
        <div className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-indigo-400" />
          <h3 className="font-bold text-white text-sm">Chat With Your Logs</h3>
        </div>
        <button onClick={onClose} className="text-zinc-400 hover:text-white">
          <X className="h-5 w-5" />
        </button>
      </div>

      {/* Suggested Query Chips */}
      <div className="p-3 bg-zinc-900/50 border-b border-zinc-800 flex gap-2 overflow-x-auto text-xs">
        {["Why did checkout timeout?", "Show customer error rate", "Find pool starvation logs"].map((chip) => (
          <button
            key={chip}
            onClick={() => handleSend(chip)}
            className="whitespace-nowrap rounded-full bg-zinc-800 hover:bg-zinc-700 px-3 py-1 text-zinc-300 transition"
          >
            {chip}
          </button>
        ))}
      </div>

      {/* Messages Feed */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 text-sm">
        {messages.map((m, idx) => (
          <div
            key={idx}
            className={`rounded-xl p-3 ${
              m.sender === "user"
                ? "ml-8 bg-purple-600 text-white"
                : "mr-4 bg-zinc-900 border border-zinc-800 text-zinc-200"
            }`}
          >
            <p className="whitespace-pre-line leading-relaxed">{m.text}</p>
            {m.citations && m.citations.length > 0 && (
              <div className="mt-3 pt-3 border-t border-zinc-800/80 space-y-1">
                <span className="text-xs font-semibold text-zinc-400">Grounding Citations:</span>
                {m.citations.slice(0, 3).map((c: any, cIdx: number) => (
                  <div key={cIdx} className="text-xs font-mono bg-zinc-950/80 rounded px-2 py-1 text-emerald-400 flex justify-between">
                    <span>{c.service}: {c.message}</span>
                    <span className="text-zinc-500">{c.citation_id}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="text-xs text-zinc-500 flex items-center gap-2">
            <Sparkles className="h-3.5 w-3.5 animate-spin text-indigo-400" />
            <span>Scanning DuckDB log records & formulating answer...</span>
          </div>
        )}
      </div>

      {/* Input Box */}
      <div className="p-3 border-t border-zinc-800 bg-zinc-900/40">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex gap-2"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question about your logs..."
            className="flex-1 rounded-xl bg-zinc-900 border border-zinc-700 px-3 py-2 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-purple-500"
          />
          <button
            type="submit"
            className="bg-purple-600 hover:bg-purple-500 text-white rounded-xl px-4 py-2 text-sm font-semibold transition flex items-center gap-1"
          >
            <Send className="h-4 w-4" />
          </button>
        </form>
      </div>
    </div>
  );
};

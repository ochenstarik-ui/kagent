"use client";

import { useEffect, useState } from "react";

interface AgentInfo {
  id: string;
  role: string;
  status: string;
  completed: number;
  errors?: number;
}

interface PipelineRun {
  task_id: string;
  status: string;
  steps: { phase: string; status: string; description: string }[];
  repair_cycles: number;
}

export default function MonitorPage() {
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [pipeline, setPipeline] = useState<PipelineRun | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/control-plane/v1/agents")
      .then(r => r.json())
      .then(d => setAgents(d.agents || []))
      .catch(() => {});

    fetch("/api/observability/v1/dashboard")
      .then(r => r.json())
      .then(d => {
        // Try to get latest pipeline
        return fetch("/api/pipeline/v1/pipelines").then(r => r.json());
      })
      .then(d => {
        if (d?.pipelines?.length > 0) {
          const last = d.pipelines[d.pipelines.length - 1];
          return fetch(`/api/pipeline/v1/pipelines/${last}`).then(r => r.json());
        }
      })
      .then((p: PipelineRun | undefined) => {
        if (p) setPipeline(p);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <main style={{ maxWidth: 1200, margin: "0 auto", padding: "2rem 1rem" }}>
      <h1 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: "2rem" }}>Pipeline & Agents</h1>

      {/* Agent Cards */}
      <section style={{ marginBottom: "2rem" }}>
        <h2 style={{ fontSize: "1.125rem", color: "#888", marginBottom: "1rem" }}>Агенты</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: "1rem" }}>
          {agents.map(a => (
            <div key={a.id} style={{
              padding: "1rem",
              background: "#1a1a2e",
              borderRadius: 8,
              border: "1px solid #333",
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                <span style={{ fontWeight: 600, textTransform: "capitalize" }}>{a.role}</span>
                <span style={{
                  width: 8, height: 8, borderRadius: "50%",
                  background: a.status === "idle" ? "#22c55e" : a.status === "busy" ? "#f59e0b" : "#ef4444",
                  display: "inline-block",
                }} />
              </div>
              <p style={{ fontSize: "0.75rem", color: "#888" }}>{a.id.slice(0, 12)}</p>
              <div style={{ display: "flex", gap: "1rem", marginTop: "0.5rem", fontSize: "0.75rem" }}>
                <span>✅ {a.completed}</span>
                <span style={{ color: "#ef4444" }}>❌ {a.errors || 0}</span>
              </div>
            </div>
          ))}
          {agents.length === 0 && !loading && (
            <p style={{ color: "#888" }}>Нет зарегистрированных агентов</p>
          )}
        </div>
      </section>

      {/* Pipeline Monitor */}
      <section>
        <h2 style={{ fontSize: "1.125rem", color: "#888", marginBottom: "1rem" }}>Pipeline</h2>
        {pipeline ? (
          <div style={{ background: "#1a1a2e", borderRadius: 12, border: "1px solid #333", padding: "1.5rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "1rem" }}>
              <span style={{ fontWeight: 600 }}>{pipeline.task_id?.slice(0, 16)}</span>
              <span style={{
                padding: "0.25rem 0.5rem", borderRadius: 4, fontSize: "0.75rem",
                background: pipeline.status === "passed" ? "#064e3b" : "#7f1d1d",
                color: pipeline.status === "passed" ? "#6ee7b7" : "#fca5a5",
              }}>{pipeline.status}</span>
            </div>
            {/* Step indicators */}
            <div style={{ display: "flex", gap: "0.25rem", marginBottom: "1rem" }}>
              {pipeline.steps?.map((s, i) => (
                <div key={i} title={`${s.phase}: ${s.description}`} style={{
                  flex: 1, height: 4, borderRadius: 2,
                  background: s.status === "passed" ? "#22c55e" : s.status === "failed" ? "#ef4444" : "#333",
                }} />
              ))}
            </div>
            <div style={{ fontSize: "0.75rem", color: "#888" }}>
              <span>Ремонтов: {pipeline.repair_cycles}</span>
              <span style={{ marginLeft: "1rem" }}>
                {pipeline.steps?.filter(s => s.status === "passed").length}/{pipeline.steps?.length} шагов
              </span>
            </div>
          </div>
        ) : (
          <div style={{
            padding: "2rem", background: "#1a1a2e", borderRadius: 12, border: "1px solid #333",
            textAlign: "center", color: "#888",
          }}>
            <p>Нет активных pipeline</p>
            <p style={{ fontSize: "0.75rem", marginTop: "0.5rem" }}>Запустите: POST /v1/pipelines/execute</p>
          </div>
        )}
      </section>
    </main>
  );
}

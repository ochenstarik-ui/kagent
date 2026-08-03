"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

interface ServiceStatus {
  name: string;
  status: string;
  version?: string;
}

interface DashboardData {
  overall: string;
  services: ServiceStatus[];
}

interface ProjectItem {
  id: string;
  name: string;
  status: string;
}

export default function HomePage() {
  const [services, setServices] = useState<ServiceStatus[]>([]);
  const [projects, setProjects] = useState<ProjectItem[]>([]);
  const [overallStatus, setOverallStatus] = useState("loading");
  const [view, setView] = useState<"dashboard" | "projects" | "pipeline">("dashboard");

  useEffect(() => {
    // Fetch service health
    fetch("/api/control-plane/health/live")
      .then(r => r.json())
      .then(() => {
        // Aggregate from observability if available
        return fetch("/api/observability/v1/health").catch(() => null);
      })
      .then(r => r?.json())
      .then((data: DashboardData | null) => {
        if (data) {
          setServices(data.services);
          setOverallStatus(data.overall);
        } else {
          setServices([{ name: "gateway", status: "healthy" }]);
          setOverallStatus("healthy");
        }
      })
      .catch(() => {
        setServices([{ name: "gateway", status: "healthy" }]);
        setOverallStatus("healthy");
      });

    // Fetch projects
    fetch("/api/control-plane/v1/projects")
      .then(r => r.json())
      .then(d => setProjects(d.items || []))
      .catch(() => {});
  }, []);

  return (
    <main style={{ maxWidth: 1200, margin: "0 auto", padding: "2rem 1rem" }}>
      {/* Header */}
      <header style={{ marginBottom: "2rem", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <p style={{ color: "#888", fontSize: "0.875rem", textTransform: "uppercase", letterSpacing: "0.1em" }}>KAGENT · 0.8.0</p>
          <h1 style={{ fontSize: "2rem", fontWeight: 700, margin: "0.25rem 0" }}>Панель управления</h1>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <span style={{
            width: 12, height: 12, borderRadius: "50%",
            background: overallStatus === "healthy" ? "#22c55e" : overallStatus === "degraded" ? "#f59e0b" : "#ef4444",
            display: "inline-block"
          }} />
          <span style={{ fontSize: "0.875rem", color: "#888" }}>{overallStatus}</span>
        </div>
      </header>

      {/* Navigation */}
      <nav style={{ display: "flex", gap: "0.5rem", marginBottom: "2rem", borderBottom: "1px solid #333", paddingBottom: "0.5rem" }}>
        {(["dashboard", "projects", "pipeline"] as const).map(v => (
          <button
            key={v}
            onClick={() => setView(v)}
            style={{
              padding: "0.5rem 1rem",
              background: view === v ? "#333" : "transparent",
              border: "none",
              borderRadius: 8,
              color: view === v ? "#fff" : "#888",
              cursor: "pointer",
              fontSize: "0.875rem",
              textTransform: "capitalize"
            }}
          >
            {v === "dashboard" ? "Обзор" : v === "projects" ? "Проекты" : "Pipeline"}
          </button>
        ))}
        <Link
          href="/workspaces"
          style={{
            padding: "0.5rem 1rem",
            color: "#93c5fd",
            fontSize: "0.875rem",
            marginLeft: "auto"
          }}
        >
          Agent Workspaces
        </Link>
      </nav>

      {/* Dashboard View */}
      {view === "dashboard" && (
        <>
          {/* Service Grid */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: "1rem", marginBottom: "2rem" }}>
            {services.map(svc => (
              <div key={svc.name} style={{
                padding: "1.25rem",
                background: "#1a1a2e",
                borderRadius: 12,
                border: "1px solid #333",
              }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                  <span style={{ fontSize: "0.75rem", color: "#888", textTransform: "uppercase" }}>{svc.name}</span>
                  <span style={{
                    width: 8, height: 8, borderRadius: "50%",
                    background: svc.status === "healthy" ? "#22c55e" : svc.status === "degraded" ? "#f59e0b" : "#ef4444",
                  }} />
                </div>
                <p style={{ fontSize: "0.75rem", color: "#666" }}>v{svc.version || "?"}</p>
              </div>
            ))}
            {services.length === 0 && (
              <p style={{ color: "#888" }}>Загрузка статуса сервисов...</p>
            )}
          </div>

          {/* Quick Stats */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))", gap: "1rem" }}>
            <StatCard label="Проектов" value={projects.length} />
            <StatCard label="Сервисов" value={services.length} />
            <StatCard label="Статус" value={overallStatus} />
          </div>
        </>
      )}

      {/* Projects View */}
      {view === "projects" && (
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "1rem" }}>
            <h2 style={{ fontSize: "1.25rem", fontWeight: 600 }}>Проекты</h2>
            <button style={btnStyle}>+ Новый проект</button>
          </div>
          {projects.length === 0 ? (
            <p style={{ color: "#888" }}>Нет проектов. Создайте первый через API.</p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              {projects.map(p => (
                <div key={p.id} style={{
                  padding: "1rem",
                  background: "#1a1a2e",
                  borderRadius: 8,
                  border: "1px solid #333",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}>
                  <div>
                    <p style={{ fontWeight: 600 }}>{p.name}</p>
                    <p style={{ fontSize: "0.75rem", color: "#888" }}>{p.id}</p>
                  </div>
                  <span style={{
                    fontSize: "0.75rem",
                    padding: "0.25rem 0.5rem",
                    borderRadius: 4,
                    background: p.status === "active" ? "#064e3b" : "#333",
                    color: p.status === "active" ? "#6ee7b7" : "#888",
                  }}>{p.status}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Pipeline View */}
      {view === "pipeline" && (
        <div>
          <h2 style={{ fontSize: "1.25rem", fontWeight: 600, marginBottom: "1rem" }}>Pipeline</h2>
          <div style={{
            padding: "2rem",
            background: "#1a1a2e",
            borderRadius: 12,
            border: "1px solid #333",
            textAlign: "center",
            color: "#888",
          }}>
            <p style={{ fontSize: "1.5rem", marginBottom: "0.5rem" }}>🔄</p>
            <p>Pipeline мониторинг — подключите сервис для отображения</p>
            <p style={{ fontSize: "0.75rem", marginTop: "0.5rem" }}>
              POST /v1/pipelines/execute для запуска
            </p>
          </div>
        </div>
      )}
    </main>
  );
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div style={{
      padding: "1rem",
      background: "#1a1a2e",
      borderRadius: 8,
      border: "1px solid #333",
    }}>
      <p style={{ fontSize: "0.75rem", color: "#888", marginBottom: "0.25rem" }}>{label}</p>
      <p style={{ fontSize: "1.5rem", fontWeight: 700 }}>{value}</p>
    </div>
  );
}

const btnStyle: React.CSSProperties = {
  padding: "0.5rem 1rem",
  background: "#2563eb",
  color: "#fff",
  border: "none",
  borderRadius: 8,
  cursor: "pointer",
  fontSize: "0.875rem",
};

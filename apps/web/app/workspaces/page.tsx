"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

interface Workspace {
  id: string;
  taskId: string;
  status: string;
  branchName: string;
  repositoryUrl: string;
  changedFiles: number;
  limits: {
    maxRuntimeMinutes: number;
    maxChangedFiles: number;
    maxConcurrentAgents: number;
    networkAccess: string;
  };
}

interface Session {
  id: string;
  kind: "agent" | "terminal" | "browser";
  title: string;
  status: string;
  agentHarness?: string;
}

interface Cockpit {
  workspace: Workspace;
  sessions: Session[];
  review: { openComments: number; resolvedComments: number };
  controls: { canPause: boolean; canResume: boolean; canCancel: boolean };
}

const statusTone: Record<string, string> = {
  running: "workspace-status workspace-status--running",
  ready: "workspace-status workspace-status--ready",
  paused: "workspace-status workspace-status--paused",
  failed: "workspace-status workspace-status--failed",
  cancelled: "workspace-status workspace-status--failed"
};

export default function WorkspacesPage() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [selectedId, setSelectedId] = useState<string>();
  const [cockpit, setCockpit] = useState<Cockpit>();
  const [error, setError] = useState<string>();

  useEffect(() => {
    fetch("/api/control-plane/v1/workspaces")
      .then(response => {
        if (!response.ok) throw new Error("Workspace API is unavailable");
        return response.json();
      })
      .then(data => {
        const items = (data.items ?? []) as Workspace[];
        setWorkspaces(items);
        setSelectedId(current => current ?? items[0]?.id);
      })
      .catch(reason => setError((reason as Error).message));
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    fetch(`/api/control-plane/v1/workspaces/${selectedId}/cockpit`)
      .then(response => {
        if (!response.ok) throw new Error("Cockpit could not be loaded");
        return response.json();
      })
      .then(data => {
        setCockpit(data as Cockpit);
        setError(undefined);
      })
      .catch(reason => setError((reason as Error).message));
  }, [selectedId]);

  const activeSessions = useMemo(
    () => cockpit?.sessions.filter(session => session.status !== "stopped").length ?? 0,
    [cockpit]
  );

  return (
    <main className="workspace-shell">
      <header className="workspace-header">
        <div>
          <Link className="workspace-back" href="/">Back to dashboard</Link>
          <p className="workspace-eyebrow">KAgent 0.10 / Workspace Provisioner</p>
          <h1>Agent workspaces</h1>
          <p className="workspace-subtitle">
            Isolated branches, governed sessions, budgets and review in one operational view.
          </p>
        </div>
        <div className="workspace-health">
          <span className="workspace-health__dot" />
          Control Plane
        </div>
      </header>

      {error && <div className="workspace-error">{error}</div>}

      <div className="workspace-grid">
        <aside className="workspace-list">
          <div className="workspace-panel-title">
            <span>Workspaces</span>
            <span>{workspaces.length}</span>
          </div>
          {workspaces.map(workspace => (
            <button
              className={`workspace-list-item ${selectedId === workspace.id ? "is-selected" : ""}`}
              key={workspace.id}
              onClick={() => setSelectedId(workspace.id)}
            >
              <span className="workspace-list-item__title">{workspace.branchName}</span>
              <span className="workspace-list-item__meta">
                <span className={statusTone[workspace.status] ?? "workspace-status"}>
                  {workspace.status}
                </span>
                {workspace.changedFiles} files
              </span>
            </button>
          ))}
          {workspaces.length === 0 && (
            <div className="workspace-empty">
              <strong>No workspaces yet</strong>
              <span>Create one with POST /v1/tasks/:taskId/workspace</span>
            </div>
          )}
        </aside>

        <section className="workspace-main">
          {cockpit ? (
            <>
              <div className="workspace-summary">
                <div>
                  <span className="workspace-label">Branch</span>
                  <strong>{cockpit.workspace.branchName}</strong>
                  <span className="workspace-repository">{cockpit.workspace.repositoryUrl}</span>
                </div>
                <span className={statusTone[cockpit.workspace.status] ?? "workspace-status"}>
                  {cockpit.workspace.status}
                </span>
              </div>

              <div className="workspace-metrics">
                <article>
                  <span>Sessions</span>
                  <strong>{activeSessions}</strong>
                  <small>of {cockpit.sessions.length} active</small>
                </article>
                <article>
                  <span>Changes</span>
                  <strong>{cockpit.workspace.changedFiles}</strong>
                  <small>limit {cockpit.workspace.limits.maxChangedFiles} files</small>
                </article>
                <article>
                  <span>Review</span>
                  <strong>{cockpit.review.openComments}</strong>
                  <small>{cockpit.review.resolvedComments} resolved</small>
                </article>
                <article>
                  <span>Runtime</span>
                  <strong>{cockpit.workspace.limits.maxRuntimeMinutes}m</strong>
                  <small>network: {cockpit.workspace.limits.networkAccess}</small>
                </article>
              </div>

              <div className="workspace-content-grid">
                <article className="workspace-card">
                  <div className="workspace-panel-title">
                    <span>Sessions</span>
                    <span>agent / terminal / browser</span>
                  </div>
                  <div className="workspace-sessions">
                    {cockpit.sessions.map(session => (
                      <div className="workspace-session" key={session.id}>
                        <span className={`workspace-session__icon workspace-session__icon--${session.kind}`}>
                          {session.kind === "agent" ? "A" : session.kind === "terminal" ? ">_" : "O"}
                        </span>
                        <div>
                          <strong>{session.title}</strong>
                          <small>{session.agentHarness ?? session.kind}</small>
                        </div>
                        <span className="workspace-session__status">{session.status}</span>
                      </div>
                    ))}
                    {cockpit.sessions.length === 0 && (
                      <div className="workspace-empty">No sessions have started.</div>
                    )}
                  </div>
                </article>

                <article className="workspace-card">
                  <div className="workspace-panel-title">
                    <span>Policy controls</span>
                    <span>default deny</span>
                  </div>
                  <dl className="workspace-policy">
                    <div><dt>Concurrent agents</dt><dd>{cockpit.workspace.limits.maxConcurrentAgents}</dd></div>
                    <div><dt>Network</dt><dd>{cockpit.workspace.limits.networkAccess}</dd></div>
                    <div><dt>Pause</dt><dd>{cockpit.controls.canPause ? "allowed" : "locked"}</dd></div>
                    <div><dt>Resume</dt><dd>{cockpit.controls.canResume ? "allowed" : "locked"}</dd></div>
                    <div><dt>Kill switch</dt><dd>{cockpit.controls.canCancel ? "armed" : "closed"}</dd></div>
                  </dl>
                </article>
              </div>
            </>
          ) : (
            <div className="workspace-placeholder">Select a workspace to open its cockpit.</div>
          )}
        </section>
      </div>
    </main>
  );
}

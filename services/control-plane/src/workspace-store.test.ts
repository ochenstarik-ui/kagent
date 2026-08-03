import { describe, expect, it } from "vitest";
import { WorkspaceStore } from "./workspace-store.js";

function createWorkspace(store: WorkspaceStore) {
  return store.createWorkspace(
    "project-123",
    "task-12345678",
    "https://github.com/example/project",
    "Add secure workspace cockpit"
  );
}

describe("WorkspaceStore", () => {
  it("creates an opaque, isolated workspace record", () => {
    const store = new WorkspaceStore();
    const workspace = createWorkspace(store);

    expect(workspace.status).toBe("provisioning");
    expect(workspace.branchName).toBe(
      "agent/add-secure-workspace-cockpit-task-123"
    );
    expect(workspace.workspaceRef).toMatch(/^workspace:/u);
    expect(workspace.workspaceRef).not.toContain("\\");
    expect(workspace.limits.networkAccess).toBe("denied");
  });

  it("enforces lifecycle transitions and verification", () => {
    const store = new WorkspaceStore();
    const workspace = createWorkspace(store);

    expect(store.transitionWorkspace(workspace.id, "running").error).toContain(
      "Invalid workspace transition"
    );
    expect(store.transitionWorkspace(workspace.id, "ready").workspace?.status).toBe("ready");
    expect(store.transitionWorkspace(workspace.id, "running").workspace?.status).toBe("running");
    expect(store.transitionWorkspace(workspace.id, "completed").error).toContain(
      "Invalid workspace transition"
    );
    expect(store.transitionWorkspace(workspace.id, "verifying").workspace?.status).toBe("verifying");
    expect(store.transitionWorkspace(workspace.id, "completed").workspace?.status).toBe("completed");
  });

  it("enforces agent concurrency limits", () => {
    const store = new WorkspaceStore();
    const workspace = createWorkspace(store);

    store.createSession(workspace.id, {
      kind: "agent",
      title: "Developer",
      agentHarness: "codex"
    });

    expect(() =>
      store.createSession(workspace.id, {
        kind: "agent",
        title: "Reviewer",
        agentHarness: "claude-code"
      })
    ).toThrow(/concurrency limit/u);
  });

  it("stores repository-relative diff comments", () => {
    const store = new WorkspaceStore();
    const workspace = createWorkspace(store);
    const comment = store.createComment(
      workspace.id,
      { path: "src/auth.ts", line: 42, side: "new", body: "Add a regression test." },
      "reviewer"
    );

    expect(store.cockpit(workspace.id)?.review.openComments).toBe(1);
    expect(store.resolveComment(workspace.id, comment.id)?.status).toBe("resolved");
    expect(() =>
      store.createComment(
        workspace.id,
        { path: "../secret", line: 1, side: "new", body: "invalid" },
        "reviewer"
      )
    ).toThrow(/repository-relative/u);
  });

  it("rejects untrusted runtime enum values", () => {
    const store = new WorkspaceStore();
    const workspace = createWorkspace(store);

    expect(() =>
      store.createSession(workspace.id, {
        kind: "shell" as "terminal",
        title: "Unsafe session"
      })
    ).toThrow(/session kind/u);

    expect(() =>
      store.createComment(
        workspace.id,
        {
          path: "src/index.ts",
          line: 1,
          side: "center" as "new",
          body: "invalid"
        },
        "reviewer"
      )
    ).toThrow(/Review side/u);
  });

  it("strips credentials from repository URLs", () => {
    const store = new WorkspaceStore();
    const workspace = store.createWorkspace(
      "project-123",
      "task-credential",
      "https://token:secret@github.com/example/project.git",
      "Credential guard"
    );

    expect(workspace.repositoryUrl).toBe("https://github.com/example/project.git");
  });

  it("issues immutable task contracts and recovers expired worker leases", () => {
    const store = new WorkspaceStore();
    const workspace = store.createWorkspace(
      "project-123",
      "task-lease",
      "https://github.com/example/project",
      "Lease recovery",
      {
        allowedPaths: ["src/**"],
        requiredChecks: ["pnpm test"]
      },
      {
        objective: "Recover work after a worker restart",
        capability: "coding",
        contextRefs: ["spec:workspace-lease"]
      }
    );

    expect(workspace.contractDigest).toMatch(/^[0-9a-f]{64}$/u);
    expect(workspace.taskContract.allowedPaths).toEqual(["src/**"]);
    expect(workspace.taskContract.requiredChecks).toEqual(["pnpm test"]);

    const first = store.acquireLease(
      workspace.id,
      "worker-a",
      30,
      new Date("2026-08-03T00:00:00.000Z")
    );
    expect(first.generation).toBe(1);
    expect(() =>
      store.acquireLease(
        workspace.id,
        "worker-b",
        30,
        new Date("2026-08-03T00:00:10.000Z")
      )
    ).toThrow(/active lease/u);

    const recovered = store.acquireLease(
      workspace.id,
      "worker-b",
      30,
      new Date("2026-08-03T00:00:31.000Z")
    );
    expect(recovered.generation).toBe(2);
    expect(() =>
      store.heartbeatLease(
        workspace.id,
        "worker-a",
        first.leaseToken,
        30,
        new Date("2026-08-03T00:00:32.000Z")
      )
    ).toThrow(/invalid/u);
    expect(
      store.heartbeatLease(
        workspace.id,
        "worker-b",
        recovered.leaseToken,
        30,
        new Date("2026-08-03T00:00:32.000Z")
      ).generation
    ).toBe(2);
  });});

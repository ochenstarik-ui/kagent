import Fastify from "fastify";
import { describe, expect, it } from "vitest";
import { Store } from "./store.js";
import { registerWorkspaceRoutes } from "./workspace-routes.js";
import { WorkspaceStore } from "./workspace-store.js";

describe("workspace routes", () => {
  it("enforces task approval and exposes restart-safe lease operations", async () => {
    const app = Fastify();
    const taskStore = new Store();
    const repository = new WorkspaceStore();
    await registerWorkspaceRoutes(app, repository, taskStore);

    const project = taskStore.createProject(
      {
        name: "Provisioner fixture",
        description: "Route integration",
        repositoryUrl: "https://github.com/example/project.git"
      },
      "owner"
    );
    const task = taskStore.createTask(
      {
        projectId: project.id,
        title: "Provision safely",
        description: "Create an idempotent worktree",
        capability: "coding",
        contextRefs: ["spec:v0.10"]
      },
      "owner"
    );

    const rejected = await app.inject({
      method: "POST",
      url: `/v1/tasks/${task.id}/workspace`,
      payload: {}
    });
    expect(rejected.statusCode).toBe(422);

    taskStore.updateTaskStatus(task.id, "planned", "owner");
    taskStore.updateTaskStatus(task.id, "approved", "owner");
    const created = await app.inject({
      method: "POST",
      url: `/v1/tasks/${task.id}/workspace`,
      payload: {
        allowedPaths: ["src/**"],
        requiredChecks: ["pnpm test"]
      }
    });
    expect(created.statusCode).toBe(201);
    const workspace = created.json();
    expect(workspace.taskContract.objective).toBe("Create an idempotent worktree");
    expect(workspace.contractDigest).toMatch(/^[0-9a-f]{64}$/u);

    const grant = await app.inject({
      method: "POST",
      url: `/v1/workspaces/${workspace.id}/lease`,
      payload: { workerId: "worker-route", ttlSeconds: 30 }
    });
    expect(grant.statusCode).toBe(201);
    const lease = grant.json();
    expect(lease.leaseToken).toBeTruthy();

    const provisioned = await app.inject({
      method: "POST",
      url: "/v1/workspaces/" + workspace.id + "/provisioning",
      payload: {
        workerId: "worker-route",
        leaseToken: lease.leaseToken,
        checkoutRef: "checkout:" + workspace.id,
        headSha: "a".repeat(40),
        status: "ready"
      }
    });
    expect(provisioned.statusCode).toBe(200);
    expect(provisioned.json().status).toBe("ready");

    const cockpit = await app.inject({
      method: "GET",
      url: "/v1/workspaces/" + workspace.id + "/cockpit"
    });
    expect(cockpit.json().workspace.status).toBe("ready");

    const heartbeat = await app.inject({
      method: "POST",
      url: `/v1/workspaces/${workspace.id}/heartbeat`,
      payload: {
        workerId: "worker-route",
        leaseToken: lease.leaseToken,
        ttlSeconds: 30
      }
    });
    expect(heartbeat.statusCode).toBe(200);
    expect(heartbeat.json().generation).toBe(1);

    const released = await app.inject({
      method: "POST",
      url: `/v1/workspaces/${workspace.id}/lease/release`,
      payload: {
        workerId: "worker-route",
        leaseToken: lease.leaseToken
      }
    });
    expect(released.statusCode).toBe(204);
    await app.close();
  });
});

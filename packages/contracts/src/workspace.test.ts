import assert from "node:assert/strict";
import test from "node:test";
import {
  assertWorkspaceTransition,
  canTransitionWorkspace
} from "./workspace.js";

test("allows pausing and resuming a running workspace", () => {
  assert.equal(canTransitionWorkspace("running", "paused"), true);
  assert.equal(canTransitionWorkspace("paused", "running"), true);
});

test("requires verification before completion", () => {
  assert.equal(canTransitionWorkspace("running", "completed"), false);
  assert.throws(
    () => assertWorkspaceTransition("running", "completed"),
    /Invalid workspace transition/u
  );
});

test("keeps completed workspaces terminal", () => {
  assert.equal(canTransitionWorkspace("completed", "running"), false);
});

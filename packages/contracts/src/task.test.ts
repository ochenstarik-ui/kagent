import assert from "node:assert/strict";
import test from "node:test";
import {
  assertTaskTransition,
  canTransitionTask
} from "./task.js";

test("allows the normal queued to planning transition", () => {
  assert.equal(canTransitionTask("queued", "planning"), true);
});

test("rejects transition from a terminal succeeded state", () => {
  assert.equal(canTransitionTask("succeeded", "running"), false);
  assert.throws(
    () => assertTaskTransition("succeeded", "running"),
    /Invalid task transition/u
  );
});

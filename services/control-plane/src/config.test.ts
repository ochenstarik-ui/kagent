import assert from "node:assert/strict";
import test from "node:test";
import { loadConfig } from "./config.js";

test("loads safe loopback defaults", () => {
  assert.deepEqual(loadConfig({}), {
    host: "127.0.0.1",
    port: 8081
  });
});

test("rejects invalid ports", () => {
  assert.throws(
    () => loadConfig({ KAGENT_CONTROL_PLANE_PORT: "70000" }),
    /Invalid TCP port/u
  );
});

import assert from "node:assert/strict";
import test from "node:test";
import { isSha256 } from "./artifact.js";

test("accepts a lowercase sha256 digest", () => {
  assert.equal(isSha256("a".repeat(64)), true);
});

test("rejects malformed digests", () => {
  assert.equal(isSha256("A".repeat(64)), false);
  assert.equal(isSha256("a".repeat(63)), false);
});

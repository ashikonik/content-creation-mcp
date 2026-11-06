// Placeholder — security regression tests are added in Stage 1 of the
// remediation plan. This file exists so the `tests/*.test.js` glob picks up a
// new test module from the start of the remediation.
import test from "node:test";
import assert from "node:assert/strict";

test("security test module is wired into the runner", () => {
  assert.equal(true, true);
});

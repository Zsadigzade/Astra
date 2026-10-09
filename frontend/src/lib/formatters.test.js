import test from "node:test";
import assert from "node:assert/strict";
import { usd } from "./formatters.js";

test("usd formats whole and fractional dollars", () => {
  assert.equal(usd(70, 1), "$70");
  assert.equal(usd(115.5, 1), "$115.5");
  assert.equal(usd(1000, 1), "$1,000");
  assert.equal(usd(null), "-");
});

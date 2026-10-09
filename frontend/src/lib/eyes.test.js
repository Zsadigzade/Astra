import test from "node:test";
import assert from "node:assert/strict";
import { FULL_AT, MAX_TILT, MAX_X, MAX_Y, eyeTarget } from "./eyes.js";

const rect = { left: 100, top: 100, width: 96, height: 120 }; // eyes at about (148, 155)

test("a cursor on the eyes keeps them centred", () => {
  assert.deepEqual(eyeTarget(rect, { x: 148, y: 155.2 }), { x: 0, y: 0, tilt: 0 });
});

test("the pupils point toward the cursor on every side", () => {
  const right = eyeTarget(rect, { x: 700, y: 155 });
  const left = eyeTarget(rect, { x: -500, y: 155 });
  const below = eyeTarget(rect, { x: 148, y: 900 });
  const above = eyeTarget(rect, { x: 148, y: -600 });
  assert.ok(right.x > 0 && left.x < 0 && below.y > 0 && above.y < 0);
  assert.ok(right.tilt > 0 && left.tilt < 0);
});

test("travel is capped at the eye's edge however far the cursor is", () => {
  const far = eyeTarget(rect, { x: 1e6, y: 155 });
  assert.equal(far.x, MAX_X);
  assert.equal(far.tilt, MAX_TILT);
  const diagonal = eyeTarget(rect, { x: 1e6, y: 1e6 });
  assert.ok(Math.hypot(diagonal.x / MAX_X, diagonal.y / MAX_Y) <= 1.001);
});

test("a nearby cursor moves the eyes less than a distant one", () => {
  const near = eyeTarget(rect, { x: 148 + FULL_AT / 4, y: 155 });
  const far = eyeTarget(rect, { x: 148 + FULL_AT * 2, y: 155 });
  assert.ok(near.x > 0 && near.x < far.x);
});

test("missing or non-finite input is safe and neutral", () => {
  const neutral = { x: 0, y: 0, tilt: 0 };
  assert.deepEqual(eyeTarget(null, { x: 1, y: 1 }), neutral);
  assert.deepEqual(eyeTarget(rect, undefined), neutral);
  assert.deepEqual(eyeTarget(rect, { x: NaN, y: 4 }), neutral);
  assert.deepEqual(eyeTarget({ ...rect, width: Infinity }, { x: 4, y: 4 }), neutral);
});

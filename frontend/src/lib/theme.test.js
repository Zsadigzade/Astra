import test from "node:test";
import assert from "node:assert/strict";
import { THEME_KEY, applyTheme, readStoredTheme, resolveTheme, storeTheme, systemTheme } from "./theme.js";

const memory = (init = {}) => {
  const d = { ...init };
  return { getItem: (k) => (k in d ? d[k] : null), setItem: (k, v) => { d[k] = String(v); }, d };
};
const media = (dark) => () => ({ matches: dark });

test("first visit follows the operating system", () => {
  assert.equal(resolveTheme(memory(), media(true)), "dark");
  assert.equal(resolveTheme(memory(), media(false)), "light");
  assert.equal(resolveTheme(memory(), undefined), "light");
});

test("an explicit choice is persisted and wins over the system preference", () => {
  const s = memory();
  assert.equal(storeTheme(s, "dark"), true);
  assert.equal(s.d[THEME_KEY], "dark");
  assert.equal(resolveTheme(s, media(false)), "dark"); // survives a reload
  storeTheme(s, "light");
  assert.equal(resolveTheme(s, media(true)), "light");
});

test("garbage in storage is ignored", () => {
  assert.equal(readStoredTheme(memory({ [THEME_KEY]: "purple" })), null);
  assert.equal(resolveTheme(memory({ [THEME_KEY]: "purple" }), media(true)), "dark");
});

test("blocked storage never throws", () => {
  const broken = { getItem() { throw new Error("denied"); }, setItem() { throw new Error("denied"); } };
  assert.equal(readStoredTheme(broken), null);
  assert.equal(storeTheme(broken, "dark"), false);
  assert.equal(resolveTheme(broken, media(true)), "dark");
  assert.equal(systemTheme(() => { throw new Error("x"); }), "light");
});

test("applyTheme sets the data attribute and color-scheme", () => {
  const root = { dataset: {}, style: {} };
  applyTheme(root, "dark");
  assert.deepEqual([root.dataset.theme, root.style.colorScheme], ["dark", "dark"]);
});

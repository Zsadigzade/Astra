import test from "node:test";
import assert from "node:assert/strict";
import { sortFlats, toCsv } from "./csv.js";

const flats = [
  { title: "Byt 2+kk", price_czk: 22000, district: "Praha 2 — Vinohrady", url: "https://www.sreality.cz/detail/1" },
  { title: 'Nice "loft", sunny', price_czk: 18000, district: "Praha 2", url: "https://www.sreality.cz/detail/2" },
];

test("csv has a header, one row per flat, and escapes quotes and commas", () => {
  const lines = toCsv(flats).split("\r\n");
  assert.equal(lines[0], "title,rent_czk,district,url");
  assert.equal(lines.length, 3);
  assert.equal(lines[2], '"Nice ""loft"", sunny",18000,Praha 2,https://www.sreality.cz/detail/2');
});

test("cells that start with a formula character are neutralised", () => {
  const out = toCsv([{ title: "=HYPERLINK(\"http://evil\")", price_czk: 1, district: "+cmd", url: "@x" }]);
  assert.ok(out.includes("\"'=HYPERLINK"), out);
  assert.ok(out.includes(",'+cmd,'@x"), out);
});

test("sorting handles numbers and Czech text in both directions without mutating", () => {
  const copy = JSON.stringify(flats);
  assert.deepEqual(sortFlats(flats, "price_czk", "asc").map((f) => f.price_czk), [18000, 22000]);
  assert.deepEqual(sortFlats(flats, "price_czk", "desc").map((f) => f.price_czk), [22000, 18000]);
  assert.equal(sortFlats(flats, "title", "asc")[0].title, 'Byt 2+kk');
  assert.equal(JSON.stringify(flats), copy);
  assert.deepEqual(toCsv([]).split("\r\n"), ["title,rent_czk,district,url"]);
});

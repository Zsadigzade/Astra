import test from "node:test";
import assert from "node:assert/strict";
import { authHeaders, withToken } from "./auth.js";
import { AudioQueue } from "../audioQueue.js";

test("no token leaves headers and URLs untouched", () => {
  assert.deepEqual(authHeaders("", { "content-type": "application/json" }), { "content-type": "application/json" });
  assert.deepEqual(authHeaders(undefined), {});
  assert.equal(withToken("http://localhost:8000/events", ""), "http://localhost:8000/events");
  assert.equal(withToken(null, "secret"), null);
});

test("token becomes a header for fetches", () => {
  assert.deepEqual(authHeaders("secret", { "content-type": "application/json" }),
    { "content-type": "application/json", "X-API-Token": "secret" });
  assert.deepEqual(authHeaders("secret"), { "X-API-Token": "secret" });
});

test("token is appended and encoded for EventSource and audio URLs", () => {
  assert.equal(withToken("http://localhost:8000/events", "secret"), "http://localhost:8000/events?token=secret");
  assert.equal(withToken("/audio/a.mp3?v=2", "a b&c"), "/audio/a.mp3?v=2&token=a%20b%26c");
  assert.equal(withToken("/audio/a.mp3#t=1", "s"), "/audio/a.mp3?token=s#t=1");
});

test("audio queue requests clips with the token", async () => {
  const urls = [];
  const queue = new AudioQueue({ buyerUrl: "http://localhost:8000/", token: "secret", createAudio: (url) => {
    urls.push(url);
    return { play: () => new Promise(() => {}), pause() {}, load() {}, removeAttribute() {} };
  }, scheduleTimeout: () => 0, cancelTimeout: () => {} });
  queue.ingest([{ id: 1, ts: 1, deal_id: "d", type: "negotiation", data: { audio_url: "/audio/one.mp3", text: "hi" } }]);
  queue.play();
  assert.deepEqual(urls, ["http://localhost:8000/audio/one.mp3?token=secret"]);
  queue.destroy();
});

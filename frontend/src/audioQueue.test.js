import test from "node:test";
import assert from "node:assert/strict";
import { AudioQueue } from "./audioQueue.js";

const event = (id) => ({ id, ts: id, deal_id: "deal", type: "negotiation", data: { audio_url: `/audio/clip${id}.mp3` } });
const tick = () => new Promise((resolve) => setImmediate(resolve));

function fakeTimers() {
  let now = 0;
  let nextId = 0;
  const pending = new Map();
  return {
    pending,
    scheduleTimeout(callback, delay) {
      const id = ++nextId;
      pending.set(id, { at: now + delay, callback });
      return id;
    },
    cancelTimeout(id) { pending.delete(id); },
    advance(ms) {
      const end = now + ms;
      while (pending.size) {
        const [id, timer] = [...pending].sort((a, b) => a[1].at - b[1].at)[0];
        if (timer.at > end) break;
        now = timer.at;
        pending.delete(id);
        timer.callback();
      }
      now = end;
    },
  };
}

function setup(play) {
  const clips = [];
  const timers = fakeTimers();
  const queue = new AudioQueue({ buyerUrl: "http://localhost:8000", ...timers, createAudio: (url) => {
    const clip = { url, paused: false, currentTime: 0, play: () => play?.(clips.length) ?? Promise.resolve(),
      pause() { this.paused = true; }, removeAttribute() {}, load() {}, end() { this.onended?.(); } };
    clips.push(clip);
    return clip;
  } });
  return { queue, clips, timers };
}

test("user enables ordered playback; SSE replay does not duplicate clips", () => {
  const { queue, clips } = setup();
  queue.ingest([event(2), event(1)]);
  assert.equal(clips.length, 0);
  queue.play();
  assert.match(clips[0].url, /clip1/);
  queue.ingest([event(1), event(2), event(3)]);
  assert.equal(clips.length, 1);
  clips[0].end();
  assert.equal(clips[0].paused, true);
  assert.match(clips[1].url, /clip2/);
  clips[1].end();
  clips[2].end();
  queue.ingest([event(1), event(2), event(3)]);
  assert.equal(clips.length, 3);
  assert.equal(queue.snapshot().playing, false);
});

test("autoplay rejection retains line for explicit user retry", async () => {
  const { queue, clips } = setup((count) => count === 1
    ? Promise.reject(Object.assign(new Error(), { name: "NotAllowedError" })) : Promise.resolve());
  queue.ingest([event(1), event(2)]);
  queue.play();
  await tick();
  assert.equal(queue.snapshot().blocked, true);
  assert.equal(queue.snapshot().queued, 2);
  queue.play();
  assert.equal(clips[1].url, clips[0].url);
  clips[1].end();
  assert.match(clips[2].url, /clip2/);
});

test("failed clip is skipped and next clip continues", async () => {
  const { queue, clips } = setup();
  queue.ingest([event(1), event(2)]);
  queue.play();
  clips[0].onerror();
  await tick();
  assert.equal(clips[0].paused, true);
  assert.match(clips[1].url, /clip2/);
  assert.equal(queue.snapshot().skipped, 1);
});

test("mute drops active and queued audio and consumes replayed events", () => {
  const { queue, clips } = setup();
  queue.ingest([event(1), event(2)]);
  queue.play();
  queue.setMuted(true);
  queue.ingest([event(1), event(2), event(3)]);
  assert.equal(clips[0].paused, true);
  assert.equal(queue.snapshot().queued, 0);
  queue.play();
  queue.ingest([event(1), event(2), event(3), event(4)]);
  assert.match(clips[1].url, /clip4/);
});

test("stop and unmount ignore a late play rejection", async () => {
  let reject;
  const { queue, clips } = setup(() => new Promise((resolve, rejectPromise) => { reject = rejectPromise; }));
  queue.ingest([event(1), event(2)]);
  queue.play();
  queue.stop();
  reject(Object.assign(new Error(), { name: "NotAllowedError" }));
  await tick();
  assert.equal(queue.snapshot().blocked, false);
  assert.equal(queue.snapshot().queued, 0);
  queue.destroy();
  queue.ingest([event(3)]);
  queue.play();
  assert.equal(clips.length, 1);
  assert.equal(clips[0].paused, true);
});

test("rejects foreign audio URLs and permits new identities after database reset", () => {
  const { queue, clips } = setup();
  queue.ingest([{ ...event(1), data: { audio_url: "https://foreign.test/file.mp3" } }, event(2)]);
  queue.play();
  clips[0].end();
  queue.ingest([{ ...event(2), ts: 99, deal_id: "new-deal" }]);
  assert.equal(clips.length, 2);
});

test("unmount releases active audio and detaches playback callbacks", async () => {
  let reject;
  const { queue, clips } = setup(() => new Promise((resolve, rejectPromise) => { reject = rejectPromise; }));
  queue.ingest([event(1), event(2)]);
  queue.play();
  const lateEnd = clips[0].onended;
  queue.destroy();
  lateEnd();
  reject(new Error("late failure"));
  await tick();
  assert.equal(clips[0].paused, true);
  assert.equal(clips[0].onended, null);
  assert.equal(clips.length, 1);
});

test("a pending play promise times out and later lines still play", async () => {
  let reject;
  const { queue, clips, timers } = setup((count) => count === 1
    ? new Promise((resolve, rejectPromise) => { reject = rejectPromise; }) : Promise.resolve());
  queue.ingest([event(1), event(2)]);
  queue.play();
  timers.advance(10000);
  await tick();
  assert.equal(clips[0].paused, true);
  assert.match(clips[1].url, /clip2/);
  assert.equal(queue.snapshot().skipped, 1);
  reject(Object.assign(new Error(), { name: "NotAllowedError" }));
  await tick();
  assert.equal(queue.snapshot().blocked, false);
  clips[1].end();
  assert.equal(timers.pending.size, 0);
});

test("only advancing playback renews the inactivity deadline", async () => {
  const { queue, clips, timers } = setup();
  queue.ingest([event(1), event(2)]);
  queue.play();
  const oldDeadline = [...timers.pending.values()][0].callback;
  timers.advance(9000);
  clips[0].currentTime = 1;
  clips[0].ontimeupdate();
  oldDeadline();
  assert.equal(queue.snapshot().skipped, 0);
  timers.advance(9000);
  clips[0].ontimeupdate();
  assert.equal(clips.length, 1);
  timers.advance(1000);
  await tick();
  assert.equal(queue.snapshot().skipped, 1);
  assert.match(clips[1].url, /clip2/);
  clips[1].end();
  assert.equal(timers.pending.size, 0);
});

test("long healthy playback survives delayed timeupdate events", () => {
  const { queue, clips, timers } = setup();
  queue.ingest([event(1)]);
  queue.play();
  for (let second = 10; second <= 40; second += 10) {
    clips[0].currentTime = second;
    timers.advance(10000);
    assert.equal(queue.snapshot().skipped, 0);
    assert.equal(queue.snapshot().playing, true);
  }
  clips[0].end();
  assert.equal(timers.pending.size, 0);
});

for (const action of ["stop", "destroy"]) {
  test(`${action} clears the watchdog and ignores late timer/progress callbacks`, async () => {
    const { queue, clips, timers } = setup();
    queue.ingest([event(1), event(2)]);
    queue.play();
    const lateDeadline = [...timers.pending.values()][0].callback;
    const lateProgress = clips[0].ontimeupdate;
    queue[action]();
    assert.equal(timers.pending.size, 0);
    assert.equal(clips[0].ontimeupdate, null);
    clips[0].currentTime = 1;
    lateProgress();
    lateDeadline();
    timers.advance(20000);
    await tick();
    assert.equal(timers.pending.size, 0);
    assert.equal(queue.snapshot().skipped, 0);
    assert.equal(clips.length, 1);
  });
}

test("default timers retain the browser global receiver", (t) => {
  const timers = fakeTimers();
  t.mock.method(globalThis, "setTimeout", function (callback, delay) {
    assert.equal(this, globalThis);
    return timers.scheduleTimeout(callback, delay);
  });
  t.mock.method(globalThis, "clearTimeout", function (timer) {
    assert.equal(this, globalThis);
    timers.cancelTimeout(timer);
  });
  const queue = new AudioQueue({ buyerUrl: "http://localhost:8000", createAudio: () => ({
    play: () => Promise.resolve(), pause() {}, removeAttribute() {}, load() {},
  }) });
  queue.ingest([event(1)]);
  queue.play();
  assert.equal(timers.pending.size, 1);
  assert.equal(queue.snapshot().playing, true);
  queue.destroy();
  assert.equal(timers.pending.size, 0);
});

import { eventKey } from "./eventIdentity.js";

// One audio element at a time. Inject createAudio for tests without a browser.
export class AudioQueue {
  constructor({ buyerUrl, createAudio = (url) => new Audio(url), onChange = () => {},
    inactivityTimeoutMs = 10000,
    scheduleTimeout = (callback, delay) => globalThis.setTimeout(callback, delay),
    cancelTimeout = (timer) => globalThis.clearTimeout(timer) }) {
    this.buyerUrl = buyerUrl.replace(/\/$/, "");
    this.createAudio = createAudio;
    this.onChange = onChange;
    this.inactivityTimeoutMs = inactivityTimeoutMs;
    this.scheduleTimeout = scheduleTimeout;
    this.cancelTimeout = cancelTimeout;
    this.pending = [];
    this.seen = new Set();
    this.current = null;
    this.enabled = false;
    this.muted = false;
    this.blocked = false;
    this.destroyed = false;
    this.skipped = 0;
  }

  snapshot() {
    return { playing: Boolean(this.current), queued: this.pending.length,
      enabled: this.enabled, muted: this.muted, blocked: this.blocked, skipped: this.skipped };
  }

  notify() { if (!this.destroyed) this.onChange(this.snapshot()); }

  ingest(events) {
    if (this.destroyed) return;
    for (const event of [...events].sort((a, b) => a.id - b.id)) {
      if (event.type !== "negotiation" || !event.data?.audio_url) continue;
      // Timestamp/deal distinguish IDs reused after a demo database reset.
      const key = eventKey(event);
      if (this.seen.has(key)) continue;
      this.seen.add(key);
      // Audio URLs come from the buyer; do not fetch arbitrary event URLs.
      if (!/^\/audio\/[a-zA-Z0-9_-]+\.mp3$/.test(event.data.audio_url)) continue;
      if (!this.muted) this.pending.push({ key, url: this.buyerUrl + event.data.audio_url });
    }
    this.pump();
    this.notify();
  }

  play() {
    if (this.destroyed) return;
    this.enabled = true;
    this.muted = false;
    this.blocked = false;
    // Called synchronously from the Play button to retain browser user activation.
    this.pump();
    this.notify();
  }

  release() {
    const active = this.current;
    this.current = null;
    if (!active) return;
    this.cancelTimeout(active.watchdog);
    active.audio.onended = null;
    active.audio.onerror = null;
    active.audio.ontimeupdate = null;
    active.audio.pause();
    active.audio.removeAttribute("src");
    active.audio.load();
  }

  stop() {
    this.enabled = false;
    this.blocked = false;
    this.pending = [];
    this.release();
    this.notify();
  }

  setMuted(muted) {
    this.muted = muted;
    if (muted) this.stop();
    this.notify();
  }

  pump() {
    if (this.destroyed || !this.enabled || this.muted || this.current || !this.pending.length) return;
    const item = this.pending.shift();
    let active;
    try {
      active = { item, audio: this.createAudio(item.url), lastTime: 0, generation: 0 };
      this.current = active;
      active.audio.onended = () => this.finish(active);
      active.audio.onerror = () => this.fail(active);
      active.audio.ontimeupdate = () => this.progress(active);
      // Covers a pending play() and playback that stops progressing without error.
      this.watch(active);
      Promise.resolve(active.audio.play()).catch((error) => this.fail(active, error));
    } catch (error) {
      if (active) this.fail(active, error);
      else {
        this.skipped += 1;
        queueMicrotask(() => this.pump());
      }
    }
    this.notify();
  }

  progress(active) {
    if (this.current !== active || this.destroyed) return false;
    const time = active.audio.currentTime;
    if (!Number.isFinite(time) || time <= active.lastTime) return false;
    active.lastTime = time;
    this.watch(active);
    return true;
  }

  watch(active) {
    this.cancelTimeout(active.watchdog);
    const generation = ++active.generation;
    active.watchdog = this.scheduleTimeout(() => {
      if (this.current !== active || this.destroyed || active.generation !== generation) return;
      // A browser can throttle timeupdate events while a tab is in the background.
      if (!this.progress(active)) this.fail(active);
    }, this.inactivityTimeoutMs);
  }

  finish(active) {
    if (this.current !== active || this.destroyed) return;
    this.release();
    this.pump();
    this.notify();
  }

  fail(active, error) {
    if (this.current !== active || this.destroyed) return;
    this.release();
    if (error?.name === "NotAllowedError") {
      this.pending.unshift(active.item);
      this.enabled = false;
      this.blocked = true;
    } else {
      this.skipped += 1;
      queueMicrotask(() => this.pump());
    }
    this.notify();
  }

  destroy() {
    this.destroyed = true;
    this.pending = [];
    this.release();
    this.seen.clear();
  }
}

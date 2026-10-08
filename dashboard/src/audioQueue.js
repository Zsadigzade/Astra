// One audio element at a time. Inject createAudio for tests without a browser.
export class AudioQueue {
  constructor({ buyerUrl, createAudio = (url) => new Audio(url), onChange = () => {} }) {
    this.buyerUrl = buyerUrl.replace(/\/$/, "");
    this.createAudio = createAudio;
    this.onChange = onChange;
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
      const key = JSON.stringify([event.id, event.ts, event.deal_id]);
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
    active.audio.onended = null;
    active.audio.onerror = null;
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
      active = { item, audio: this.createAudio(item.url) };
      this.current = active;
      active.audio.onended = () => this.finish(active);
      active.audio.onerror = () => this.fail(active);
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

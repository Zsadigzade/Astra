import { useEffect } from "react";
import { eyeTarget } from "../lib/eyes.js";

// Points a ghost's pupils (CSS vars --px/--py) and head (--tilt) at the cursor while `enabled`.
// Off for reduced motion; on a touch screen it follows the finger while dragging. The vars are cleared when it stops.
export default function useCursorEyes(ref, enabled) {
  useEffect(() => {
    const el = ref.current;
    if (!el) return undefined;
    const reduced = !!window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    const clear = () => ["--px", "--py", "--tilt"].forEach((v) => el.style.removeProperty(v));
    if (!enabled || reduced) { clear(); return undefined; }

    let frame = 0;
    let pointer = null;
    const apply = () => {
      frame = 0;
      if (!pointer) { clear(); return; }
      const t = eyeTarget(el.getBoundingClientRect(), pointer);
      el.style.setProperty("--px", t.x);
      el.style.setProperty("--py", t.y);
      el.style.setProperty("--tilt", t.tilt);
    };
    const schedule = () => { if (!frame) frame = requestAnimationFrame(apply); };
    const onMove = (e) => { pointer = { x: e.clientX, y: e.clientY }; schedule(); };
    const onLeave = () => { pointer = null; schedule(); };

    window.addEventListener("pointermove", onMove, { passive: true });
    document.documentElement.addEventListener("pointerleave", onLeave);
    window.addEventListener("blur", onLeave);
    return () => {
      window.removeEventListener("pointermove", onMove);
      document.documentElement.removeEventListener("pointerleave", onLeave);
      window.removeEventListener("blur", onLeave);
      if (frame) cancelAnimationFrame(frame);
      clear();
    };
  }, [ref, enabled]);
}

import { useRef } from "react";
import useCursorEyes from "../hooks/useCursorEyes.js";

// A small floating ghost. All motion is CSS (see styles.css) and is switched off under prefers-reduced-motion.
// mood: idle | thinking | speaking. `who` only picks the colour and which way it faces.
export default function Ghost({ who, mood = "idle", tracking = false }) {
  const root = useRef(null);
  useCursorEyes(root, tracking && mood === "idle"); // motion only: the eyes follow the cursor
  return (
    <div ref={root} className={`ghost ghost-${who} is-${mood}`} aria-hidden="true">
      <svg viewBox="0 0 80 100" width="76" height="95" focusable="false">
        <ellipse className="ghost-shadow" cx="40" cy="95" rx="22" ry="4" />
        <g className="ghost-body">
          <path className="ghost-fill" d="M9 54 C9 25 23 9 40 9 C57 9 71 25 71 54 L71 84 L63 76 L55 86 L47 76 L40 86 L33 76 L25 86 L17 76 L9 84 Z" />
          <ellipse className="ghost-shine" cx="26" cy="28" rx="7" ry="10" transform="rotate(25 26 28)" />
          <g className="ghost-eyes">
            <ellipse className="ghost-eye" cx="30" cy="46" rx="5" ry="7" />
            <ellipse className="ghost-eye" cx="50" cy="46" rx="5" ry="7" />
            <circle className="ghost-glint" cx="32" cy="43" r="1.6" />
            <circle className="ghost-glint" cx="52" cy="43" r="1.6" />
          </g>
          <ellipse className="ghost-mouth" cx="40" cy="62" rx="5" ry="3" />
        </g>
      </svg>
    </div>
  );
}

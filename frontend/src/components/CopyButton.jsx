import { useEffect, useState } from "react";
import Icon from "./Icons.jsx";

export default function CopyButton({ text, label = "Copy", className = "", showLabel = false }) {
  const [copied, setCopied] = useState(false);
  useEffect(() => {
    if (!copied) return undefined;
    const t = setTimeout(() => setCopied(false), 1600);
    return () => clearTimeout(t);
  }, [copied]);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
    } catch {
      // Clipboard can be blocked (insecure origin); fall back to a selection the person can copy by hand.
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      try { setCopied(document.execCommand("copy")); } finally { ta.remove(); }
    }
  };

  return (
    <button type="button" className={`icon-btn ${className}`} onClick={copy} aria-label={copied ? "Copied" : label}
      title={copied ? "Copied" : label}>
      <Icon name={copied ? "check" : "copy"} size={14} />
      {showLabel ? <span>{copied ? "Copied" : label}</span> : copied && <span className="copied-note">Copied</span>}
      <span className="sr-only" role="status">{copied ? "Copied to clipboard" : ""}</span>
    </button>
  );
}

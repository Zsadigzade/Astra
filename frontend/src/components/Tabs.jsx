import { useRef } from "react";

// Accessible tab bar: arrow keys move between tabs, Home/End jump. `extra` sits at the right end.
export default function Tabs({ tabs, value, onChange, extra }) {
  const refs = useRef({});
  const move = (e, i) => {
    const next = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: tabs.length - 1 }[e.key];
    if (next === undefined) return;
    e.preventDefault();
    const t = tabs[(next + tabs.length) % tabs.length];
    onChange(t.id);
    refs.current[t.id]?.focus();
  };
  return (
    <div className="tabbar">
      <div role="tablist" aria-label="Deal views" className="tabs">
        {tabs.map((t, i) => (
          <button key={t.id} ref={(el) => { refs.current[t.id] = el; }} type="button" role="tab" id={`tab-${t.id}`}
            aria-selected={value === t.id} aria-controls={`panel-${t.id}`} tabIndex={value === t.id ? 0 : -1}
            className={`tab ${value === t.id ? "is-on" : ""}`} onClick={() => onChange(t.id)} onKeyDown={(e) => move(e, i)}>
            {t.label}{t.count != null && t.count > 0 && <span className="tab-count">{t.count}</span>}
          </button>
        ))}
      </div>
      {extra && <div className="tab-extra">{extra}</div>}
    </div>
  );
}

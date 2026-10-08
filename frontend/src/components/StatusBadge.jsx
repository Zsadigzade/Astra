import Icon from "./Icons.jsx";

const ICON = { success: "check", warning: "alert", danger: "x", info: "info", neutral: null };

// Small semantic badge. Tone is never the only signal: the text always says what it means.
export default function StatusBadge({ tone = "neutral", children, title, icon, className = "" }) {
  const name = icon === undefined ? ICON[tone] : icon;
  return (
    <span className={`badge badge-${tone} ${className}`} title={title}>
      {name && <Icon name={name} size={12} />}
      {children}
    </span>
  );
}

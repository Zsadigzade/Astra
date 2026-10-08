import Icon from "./Icons.jsx";

export default function ThemeToggle({ theme, onToggle }) {
  const next = theme === "dark" ? "light" : "dark";
  return (
    <button type="button" className="icon-btn icon-btn-lg" onClick={onToggle}
      aria-label={`Switch to ${next} theme`} title={`Switch to ${next} theme`}>
      <Icon name={theme === "dark" ? "sun" : "moon"} size={18} />
    </button>
  );
}

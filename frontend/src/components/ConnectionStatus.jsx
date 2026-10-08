import Icon from "./Icons.jsx";

const STATE = {
  online: { icon: "check", text: "Online", tone: "success" },
  degraded: { icon: "alert", text: "Degraded", tone: "warning" },
  connecting: { icon: "refresh", text: "Connecting", tone: "warning" },
  reconnecting: { icon: "refresh", text: "Reconnecting", tone: "warning" },
  offline: { icon: "x", text: "Offline", tone: "danger" },
  unknown: { icon: "info", text: "Unknown", tone: "neutral" },
};

// Quiet status list: icon + text + color, so state never relies on color alone.
export default function ConnectionStatus({ items }) {
  return (
    <ul className="conn" aria-label="Service status">
      {items.map(({ name, state, detail }) => {
        const s = STATE[state] ?? STATE.unknown;
        return (
          <li key={name} className={`conn-item conn-${s.tone}`} title={detail}>
            <Icon name={s.icon} size={13} className={state === "connecting" || state === "reconnecting" ? "spin" : ""} />
            <span className="conn-name">{name}</span>
            <span className="conn-state">{detail ?? s.text}</span>
          </li>
        );
      })}
    </ul>
  );
}

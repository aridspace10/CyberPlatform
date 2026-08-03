import './Switch.css'

export default function Switch({ on, onChange }) {
  return (
    <div
      onClick={() => onChange(!on)}
      className={`switch-track ${on ? "switch-on" : ""}`}
    >
      <div className="switch-thumb" />
    </div>
  );
}
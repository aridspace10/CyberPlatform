export default function Switch({ on, onChange }) {
  return (
    <div
      onClick={() => onChange(!on)}
      style={{
        width: 50,
        height: 26,
        borderRadius: 13,
        background: on ? "#4CAF50" : "#ccc",
        position: "relative",
        cursor: "pointer",
        transition: "background 0.2s",
      }}
    >
      <div style={{
        width: 22,
        height: 22,
        borderRadius: "50%",
        background: "white",
        position: "absolute",
        top: 2,
        left: on ? 26 : 2,
        transition: "left 0.2s",
      }} />
    </div>
  );
}
import { useState } from "react";

function Terminal() {
  const [command, setCommand] = useState("");
  const [output, setOutput] = useState("");

  const runCommand = async () => {
    const res = await fetch("http://127.0.0.1:8000/command", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ command })
    });

    const data = await res.json();
    setOutput(prev => prev + "\n" + data.stdout);
    setCommand("");
  };

  return (
    <div>
      <pre>{output}</pre>

      <input
        value={command}
        onChange={e => setCommand(e.target.value)}
        onKeyDown={e => e.key === "Enter" && runCommand()}
      />

      <button onClick={runCommand}>Run</button>
    </div>
  );
}

export default Terminal;

import { useEffect, useRef, useState } from "react";
import "./Terminal.css";

export default function Terminal() {

  const wsRef = useRef(null);

  const [log, setLog] = useState([]);
  const [input, setInput] = useState("");
  const [username, setUsername] = useState("");

  const sessionId = "test123";

  // ----------------------
  // Ask username once
  // ----------------------
  useEffect(() => {
    const name = prompt("Enter username");
    setUsername(name || "anonymous");
  }, []);

  // ----------------------
  // Connect socket AFTER username set
  // ----------------------
  useEffect(() => {

    if (!username) return;
    if (wsRef.current) return;

    const socket = new WebSocket(
      `ws://localhost:8000/ws/${sessionId}`
    );

    socket.onopen = () => {
      socket.send(JSON.stringify({
        type: "join",
        username: username
      }));
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === "chat") {
        addLine(`${data.user}: ${data.message}`);
      }

      if (data.type === "system") {
        addLine(`[SYSTEM] ${data.message}`);
      }

      if (data.type === "command_output") {
        data.stdout.forEach(line => addLine(line));
        data.stderr.forEach(line => addLine(line));
      }
    };

    wsRef.current = socket;

    return () => {
      socket.close();
      wsRef.current = null;
    };

  }, [username]);

  // ----------------------
  // Helpers
  // ----------------------
  function addLine(text) {
    setLog(prev => [...prev, text]);
  }

  function handleEnter(e) {
    if (e.key === "Enter") {

      if (!wsRef.current || wsRef.current.readyState !== 1) {
        addLine("[SYSTEM] Not connected");
        return;
      }

      if (input.startsWith("/chat ")) {
        wsRef.current.send(JSON.stringify({
          type: "chat",
          message: input.substring(6)
        }));
      }
      else {
        wsRef.current.send(JSON.stringify({
          type: "command",
          input: input
        }));
      }

      addLine("> " + input);
      setInput("");
    }
  }

  return (
    <div className="terminal">

      <div className="output">
        {log.map((line, i) => (
          <div key={i}>{line}</div>
        ))}
      </div>

      <input
        className="prompt"
        value={input}
        onChange={e => setInput(e.target.value)}
        onKeyDown={handleEnter}
        autoFocus
      />

    </div>
  );
}

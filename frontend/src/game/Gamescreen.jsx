import { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router";
import Terminal from "./Terminal";
export default function Gamescreen({wsRef, log}) {
  const [input, setInput] = useState("");

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

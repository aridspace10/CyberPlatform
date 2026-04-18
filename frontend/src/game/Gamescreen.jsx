import { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router";
import Terminal from "./Terminal";
import "./Gamescreen.css"
export default function Gamescreen({wsRef, commandLog, addCommandLine}) {
    const [input, setInput] = useState("");

    function handleTerminalEnter(e) {
        if (e.key === "Enter") {
            if (!wsRef.current || wsRef.current.readyState !== 1) {
                addCommandLine("[SYSTEM] Not connected");
                return;
            }
            wsRef.current.send(JSON.stringify({
                type: "command",
                input: input
            }));
            addCommandLine("> " + input);
            setInput("");
        }
    }

    return (
        <div className="gamescreen">
            <div className="terminal">
                <div className="output">
                    {commandLog.map((line, i) => (
                    <div key={i}>{line}</div>
                    ))}
                </div>
                <input
                    className="prompt"
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    onKeyDown={handleTerminalEnter}
                    autoFocus
                />
            </div>
        </div>
    );
}

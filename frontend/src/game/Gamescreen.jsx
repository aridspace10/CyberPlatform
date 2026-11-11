import { useEffect, useRef, useState } from "react";
import "./Gamescreen.css"
export default function Gamescreen({wsRef, commandLog, addCommandLine, username, cwd}) {
    const [input, setInput] = useState("");
    const inputRef = useRef(null);

    useEffect(() => {
        inputRef.current?.focus();
    }, []);

    function handleTerminalEnter(e) {
        if (e.key === "Enter") {
            if (!input.trim()) return;
            if (!wsRef.current || wsRef.current.readyState !== 1) {
                addCommandLine("[SYSTEM] Not connected");
                return;
            }
            wsRef.current.send(JSON.stringify({
                type: "command",
                input: input
            }));
            addCommandLine(`${username || "user"}@cyber:${formatPath(cwd)}$ ${input}`);
            setInput("");
        }
    }

    function formatPath(path) {
        if (!path || path === "/root") return "~";
        if (path.startsWith("/root/")) return `~${path.slice(5)}`;
        return path;
    }

    return (
        <div className="gamescreen">
            <div className="terminal" onClick={() => inputRef.current?.focus()}>
                <div className="output">
                    {commandLog.map((line, i) => (
                    <div key={i}>{line}</div>
                    ))}
                    <div className="prompt-row">
                        <span className="prompt-label">
                            {username || "user"}@cyber:{formatPath(cwd)}$
                        </span>
                        <input
                            ref={inputRef}
                            className="prompt"
                            value={input}
                            onChange={e => setInput(e.target.value)}
                            onKeyDown={handleTerminalEnter}
                            aria-label="Terminal command"
                            spellCheck="false"
                            autoFocus
                        />
                    </div>
                </div>
            </div>
        </div>
    );
}

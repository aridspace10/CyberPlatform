import { useEffect, useRef, useState } from "react";
import "./Gamescreen.css"
export default function Gamescreen({wsRef, commandLog, addCommandLine, username, cwd}) {
    const [input, setInput] = useState("");
    const [history, setHistory] = useState([]);
    const [historyIndex, setHistoryIndex] = useState(null);
    const draftRef = useRef("");
    const inputRef = useRef(null);

    useEffect(() => {
        inputRef.current?.focus();
    }, []);

    function navigateHistory(direction) {
        if (!history.length) return;

        if (direction < 0) {
            if (historyIndex === null) draftRef.current = input;
            const nextIndex = historyIndex === null
                ? history.length - 1
                : Math.max(0, historyIndex - 1);
            setHistoryIndex(nextIndex);
            setInput(history[nextIndex]);
        } else if (historyIndex !== null) {
            const nextIndex = historyIndex + 1;
            if (nextIndex < history.length) {
                setHistoryIndex(nextIndex);
                setInput(history[nextIndex]);
            } else {
                setHistoryIndex(null);
                setInput(draftRef.current);
            }
        }
        window.requestAnimationFrame(() => {
            const field = inputRef.current;
            if (!field) return;
            field.focus();
            field.setSelectionRange(field.value.length, field.value.length);
        });
    }

    function handleTerminalEnter(e) {
        if (e.key === "ArrowUp" || e.key === "ArrowDown") {
            e.preventDefault();
            navigateHistory(e.key === "ArrowUp" ? -1 : 1);
            return;
        }
        if (e.key !== "Enter" || !input.trim()) return;
        if (!wsRef.current || wsRef.current.readyState !== 1) {
            addCommandLine("[SYSTEM] Not connected");
            return;
        }
        wsRef.current.send(JSON.stringify({
            type: "command",
            input: input
        }));
        addCommandLine(`${username || "user"}@cyber:${formatPath(cwd)}$ ${input}`);
        setHistory(previous => [...previous, input].slice(-100));
        setHistoryIndex(null);
        draftRef.current = "";
        setInput("");
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
                        <div className="history-controls" aria-label="Command history">
                            <button type="button" title="Previous command (Up arrow)" aria-label="Previous command" disabled={!history.length} onClick={() => navigateHistory(-1)}>↑</button>
                            <button type="button" title="Next command (Down arrow)" aria-label="Next command" disabled={historyIndex === null} onClick={() => navigateHistory(1)}>↓</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

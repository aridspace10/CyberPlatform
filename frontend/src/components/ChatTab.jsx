import "./Tabs.css"
import { useEffect, useRef, useState } from "react";

export default function ChatTab({wsRef, chatLog}) {
    const [input, setInput] = useState("");
    function handleChatEnter(e) {
        if (e.key === "Enter") {
            if (!wsRef.current || wsRef.current.readyState !== 1) {
                addLine("[SYSTEM] Not connected");
                return;
            }

            wsRef.current.send(JSON.stringify({
                type: "chat",
                message: input
            }));
            setInput("");
        }
    }

    return (
        <div className="chat-tab">
            <h1> Chat </h1>
            <div className="output">
                {chatLog.map((line, i) => (
                <div key={i}>{line}</div>
                ))}
            </div>
            <input
                className="prompt"
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleChatEnter}
                autoFocus
            />
        </div>
    )
}
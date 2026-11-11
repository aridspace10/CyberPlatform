import { useEffect, useRef, useState } from "react";
import "./ChatTab.css";

export default function ChatTab({ wsRef, chatLog, username }) {
    const [input, setInput] = useState("");
    const [error, setError] = useState("");
    const endRef = useRef(null);

    useEffect(() => {
        endRef.current?.scrollIntoView({ block: "end" });
    }, [chatLog]);

    function handleSend(event) {
        event.preventDefault();
        const message = input.trim();
        if (!message) return;
        if (wsRef.current?.readyState !== WebSocket.OPEN) {
            setError("Chat is disconnected. Try again when the session reconnects.");
            return;
        }

        wsRef.current.send(JSON.stringify({ type: "chat", message }));
        setInput("");
        setError("");
    }

    return (
        <section className="chat-tab" aria-label="Session chat">
            <header className="chat-header">
                <h1>Chat</h1>
                <p>Messages in this session</p>
            </header>
            <div className="chat-messages" role="log" aria-live="polite" aria-relevant="additions">
                {chatLog.length === 0 && (
                    <p className="chat-empty">No messages yet. Start the conversation.</p>
                )}
                {chatLog.map((entry, index) => {
                    const sender = typeof entry?.user === "string" ? entry.user : "Player";
                    const message = typeof entry?.message === "string" ? entry.message : "";
                    const ownMessage = sender === username;
                    return (
                        <div className={`chat-message${ownMessage ? " own" : ""}`} key={index}>
                            <span className="chat-sender">{ownMessage ? "You" : sender}</span>
                            <p>{message}</p>
                        </div>
                    );
                })}
                <div ref={endRef} />
            </div>
            <form className="chat-compose" onSubmit={handleSend}>
                <label className="visually-hidden" htmlFor="session-chat-message">Message</label>
                <input
                    id="session-chat-message"
                    value={input}
                    onChange={event => setInput(event.target.value)}
                    placeholder="Type a message..."
                    autoComplete="off"
                />
                <button type="submit" disabled={!input.trim()} aria-label="Send message">Send</button>
            </form>
            {error && <p className="chat-error" role="alert">{error}</p>}
        </section>
    );
}

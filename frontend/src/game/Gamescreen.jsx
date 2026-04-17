import { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router";
import GeneralTab from "../components/GeneralTab";
import EnvironmentTab from "../components/EnvironmentTab";
import SettingsTab from "../components/SettingsTab";
import Terminal from "./Terminal";
import "./Gamescreen.css"
export default function Gamescreen({wsRef, chatLog, commandLog, addChatLine, addCommandLine}) {
  const [input, setInput] = useState("");
  const [content, setContent] = useState(<GeneralTab />)

    function handleChatEnter(e) {
        if (e.key === "Enter") {
            if (!wsRef.current || wsRef.current.readyState !== 1) {
                addLine("[SYSTEM] Not connected");
                return;
            }

            wsRef.current.send(JSON.stringify({
            type: "chat",
            message: input.substring(6)
            }));
        }
    }

    function handleTerminalEnter(e) {
        if (e.key === "Enter") {
            if (!wsRef.current || wsRef.current.readyState !== 1) {
                addLine("[SYSTEM] Not connected");
                return;
            }
            wsRef.current.send(JSON.stringify({
                type: "command",
                input: input
            }));
            addLine("> " + input);
            setInput("");
        }
    }

    const handleTabSwitch = (tab) => {
        console.log("please")
        switch (tab) {
            case "General":
                setContent(<GeneralTab />)
                break;
            case "Settings":
                setContent(<SettingsTab />)
                break;
            case "Environment":
                setContent(<EnvironmentTab />)
                break;
        }
    }

  return (
    <div className="gamescreen">
        <div className="sidebar-page">
            <div className="sidebar-nav">
                <button onClick={() => handleTabSwitch("General")}> General </button>
                <button onClick={() => handleTabSwitch("Settings")}> Settings </button>
                <button onClick={() => handleTabSwitch("Environment")}> Environment </button>
            </div>
            {content}
        </div> 

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
                onKeyDown={handleTerminalEnter}
                autoFocus
            />
        </div>
    </div>
  );
}

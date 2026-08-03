<<<<<<< HEAD
import { useState } from "react";
import GeneralTab from "../components/GeneralTab";
import EnvironmentTab from "../components/EnvironmentTab";
import SettingsTab from "../components/SettingsTab";
import Terminal from "./Terminal";
import "./Gamescreen.css"
export default function Gamescreen({wsRef, log, addLine, interaction}) {
  const [input, setInput] = useState("");
  const [content, setContent] = useState(<GeneralTab />)

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

    const handleTabSwitch = (tab) => {
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
=======
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
>>>>>>> 242b85d5bcb3b4be280bd170ccc8c8ad2559e8bb
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
<<<<<<< HEAD
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
                onKeyDown={handleEnter}
                disabled={interaction === "foreground"}
                autoFocus
            />
=======
>>>>>>> 242b85d5bcb3b4be280bd170ccc8c8ad2559e8bb
        </div>
    );
}

import { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router";
import GeneralTab from "../components/GeneralTab";
import EnvironmentTab from "../components/EnvironmentTab";
import SettingsTab from "../components/SettingsTab";
import Terminal from "./Terminal";
import "./Gamescreen.css"
export default function Gamescreen({wsRef, log, addLine}) {
  const [input, setInput] = useState("");
  const [content, setContent] = useState(<GeneralTab />)
    const [commandCount, setCommandCount] = useState(-1);
    const getCommand = (count) => {
        if (count === -1) {
            setInput("");
        }

        
    }

    const handleKeyDown = (e) => {
        switch (e.key) {
            case 'ArrowUp':
                commandCount += 1
                getCommand(count);
                break;
            case 'ArrowDown':
                if (commandCount >= 0) {
                    commandCount -= 1;
                    getCommand(count);
                }
                break;
            case 'ArrowLeft':  
                break;
            case 'ArrowRight': 
                break;
        }
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
                onKeyDown={handleEnter}
                autoFocus
            />
        </div>
    </div>
  );
}

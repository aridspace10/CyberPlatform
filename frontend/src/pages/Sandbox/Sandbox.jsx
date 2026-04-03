import SettingsTab from "../../components/SettingsTab"
import GeneralTab from "../../components/GeneralTab"
import { useEffect, useRef, useState } from "react";
import EnvironmentTab from "../../components/EnvironmentTab"
import { useParams } from "react-router-dom";
import Gamescreen from "../../game/Gamescreen";

export default function Sandbox() {
    let content = <GeneralTab />
    const [log, setLog] = useState([]);
    const wsRef = useRef(null);
    const { sessionId } = useParams();

    function addLine(text) {
        setLog(prev => [...prev, text]);
    }

    const handleTabSwitch = (tab) => {
        switch (tab) {
            case "General":
                content = <GeneralTab />
            case "Settings":
                content = <SettingsTab />
            case "Environment":
                content = <EnvironmentTab />
        }
    }

    return (
        <div className="sandbox-page">
            <div className="main-screen">
                <Gamescreen wsRef={wsRef} log={log} addLine={addLine} />
            </div>
            <div className="sidebar-page">
                <div className="sidebar-nav">
                    <button onClick={() => handleTabSwitch("General")}> General </button>
                    <button onClick={() => handleTabSwitch("Settings")}> Settings </button>
                    <button onClick={() => handleTabSwitch("Environment")}> Environment </button>
                </div>
                {content}
            </div>
        </div>
    )
}
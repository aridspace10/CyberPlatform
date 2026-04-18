import { useScroll } from "motion/react";
import { useContext, useEffect, useRef, useState } from "react";
import { useLocation } from "react-router";
import Gamescreen from "./Gamescreen";
import WaitingScreen from "./WaitingScreen";
import Versus from "./Versus";
import { useParams } from "react-router-dom";
import { useAuth } from "../auth/useAuth";
import { getFullSessionData } from "../api/sessions";
import { SessionContext } from "../components/SessionContext";
import GeneralTab from "../components/GeneralTab";
import EnvironmentTab from "../components/EnvironmentTab";
import SettingsTab from "../components/SettingsTab";
import ChatTab from "../components/ChatTab"
import "./Gamescreen.css"

export default function Game() {
    const location = useLocation();
    const { sessionId } = useParams();
    const { user } = useAuth()
    const [sessionData, setSessionData] = useState(null);
    const [players, setPlayers] = useState([]);
    const [username, setUsername] = useState("");
    const wsRef = useRef(null);
    const hasPrompted = useRef(false);
    const [commandLog, setCommandLog] = useState([]);
    const [chatLog, setChatLog] = useState([]);
    const [state, setState] = useState(null);
    const [sidebar, setSidebar] = useState(null);
    const [mainbar, setMainbar] = useState(null);
    const [activeTab, setActiveTab] = useState(null);

    function addCommandLine(text) {
        setCommandLog(prev => [...prev, text]);
    }

    function addChatLine(text) {
        setChatLog(prev => [...prev, text]);
    }

    const hasConnected = useRef(false);

    useEffect(() => {
        if (!user || wsRef.current) return;

        const socket = new WebSocket(
            `ws://localhost:8000/ws/${sessionId}`
        );

        socket.onopen = async () => {
            socket.send(JSON.stringify({
                type: "join",
                username: user.username,
                userID: user.id
            }));

            const sessionData = await getFullSessionData(sessionId, user.id);
            console.log(sessionData)
            setState(sessionData["state"]);
        };

        socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log("WS message:", data);

            if (data.type === "chat") {
                addChatLine(`${data.user}: ${data.message}`);
            }

            if (data.type === "lobby_update") {
                setPlayers(data.players);
                setState(data.state);
                return;
            }

            if (data.type === "system") {
                addCommandLine(`[SYSTEM] ${data.message}`);
            }

            if (data.type === "command_output") {
                console.log("hey")
                data.stdout.forEach(line => addCommandLine(line));
                data.stderr.forEach(line => addCommandLine(line));
            }
        };

        wsRef.current = socket;

        return () => {
            socket.close();
            wsRef.current = null;
        };
    }, [user, sessionId]);

    const handleTabSwitch = (tab) => {
        setActiveTab(tab);
    };

    return (
        <div className="game">
            <div className="sidebar-page">
                <div className="sidebar-nav">
                    <button onClick={() => handleTabSwitch("General")}> General </button>
                    <button onClick={() => handleTabSwitch("Settings")}> Settings </button>
                    <button onClick={() => handleTabSwitch("Environment")}> Environment </button>
                    <button onClick={() => handleTabSwitch("Chat")}> Chat </button>
                </div>
                {activeTab === "General" && <GeneralTab />}
                {activeTab === "Settings" && <SettingsTab />}
                {activeTab === "Environment" && <EnvironmentTab />}
                {activeTab === "Chat" && <ChatTab wsRef={wsRef} chatLog={chatLog} />}
            </div> 
            {state === "waiting" && <WaitingScreen players={players} />}
            {state === "running" && (
                <SessionContext.Provider value={{ sessionId, wsRef }}>
                    <Gamescreen wsRef={wsRef} commandLog={commandLog} addCommandLine={addCommandLine} />
                </SessionContext.Provider>
            )}
            {state === "starting" && <Versus players={players} />}
            {!state && <h1>Loading...</h1>}
        </div>
    )
}
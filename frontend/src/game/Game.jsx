import { useEffect, useRef, useState } from "react";
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
    const { sessionId } = useParams();
    const { user } = useAuth()
    const [players, setPlayers] = useState([]);
    const wsRef = useRef(null);
<<<<<<< HEAD
    const [log, setLog] = useState([]);
    const [state, setState] = useState("")
    const [interaction, setInteraction] = useState("")
=======
    const hasPrompted = useRef(false);
    const [commandLog, setCommandLog] = useState([]);
    const [chatLog, setChatLog] = useState([]);
    const [state, setState] = useState(null);
    const [sidebar, setSidebar] = useState(null);
    const [mainbar, setMainbar] = useState(null);
    const [activeTab, setActiveTab] = useState(null);
>>>>>>> 242b85d5bcb3b4be280bd170ccc8c8ad2559e8bb

    function addCommandLine(text) {
        setCommandLog(prev => [...prev, text]);
    }

    function addChatLine(text) {
        setChatLog(prev => [...prev, text]);
    }

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
            setState(sessionData["state"]);
        };

        socket.onmessage = (event) => {
            const data = JSON.parse(event.data);

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
<<<<<<< HEAD
                const stdout = Array.isArray(data.stdout) ? data.stdout : [];
                const stderr = Array.isArray(data.stderr) ? data.stderr : [];
                stdout.forEach(line => addLine(line));
                stderr.forEach(line => addLine(line));
                if (data.interaction && data.interaction.mode) {
                    setInteraction(data.interaction.mode);
                } else {
                    setInteraction("");
                }
                const prompt = data.interaction?.prompt;
                if (prompt) addLine(prompt);
            }

            if (data.type === "terminal_state") {
                setInteraction(data.busy ? "foreground" : "")
=======
                console.log("hey")
                data.stdout.forEach(line => addCommandLine(line));
                data.stderr.forEach(line => addCommandLine(line));
>>>>>>> 242b85d5bcb3b4be280bd170ccc8c8ad2559e8bb
            }
        };

        wsRef.current = socket;

        return () => {
            socket.close();
            wsRef.current = null;
        };
    }, [user, sessionId]);

<<<<<<< HEAD
    if (state == 'waiting') {
        return (<WaitingScreen players={players} />)
    } else if (state == 'running') {
        return (
            <SessionContext.Provider value={{ sessionId, wsRef }}>
                <Gamescreen wsRef={wsRef} log={log} addLine={addLine} interaction={interaction} />
            </SessionContext.Provider>
    )
    } else if (state == 'starting') {
        return (<Versus players={players} />)
    } else {
        return (
            <h1> Loading... </h1>
        )
    }
}
=======
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
>>>>>>> 242b85d5bcb3b4be280bd170ccc8c8ad2559e8bb

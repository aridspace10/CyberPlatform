import { useEffect, useRef, useState } from "react";
import Gamescreen from "./Gamescreen";
import WaitingScreen from "./WaitingScreen";
import Versus from "./Versus";
import GameDataPanel from "./GameDataPanel";
import { useParams } from "react-router-dom";
import { useAuth } from "../auth/useAuth";
import { getFullSessionData } from "../api/sessions";
import { SessionContext } from "../components/SessionContext";
import GeneralTab from "../components/GeneralTab";
import EnvironmentTab from "../components/EnvironmentTab";
import SettingsTab from "../components/SettingsTab";
import ChatTab from "../components/ChatTab"
import { WEBSOCKET_URL } from "../api/config";
import "./Gamescreen.css"

export default function Game() {
    const { sessionId } = useParams();
    const { user } = useAuth()
    const [players, setPlayers] = useState([]);
    const wsRef = useRef(null);
    const [commandLog, setCommandLog] = useState([]);
    const [chatLog, setChatLog] = useState([]);
    const [state, setState] = useState(null);
    const [gameData, setGameData] = useState(null);
    const [activeTab, setActiveTab] = useState("General");
    const [cwd, setCwd] = useState("/");

    function addCommandLine(text) {
        setCommandLog(prev => [...prev, text]);
    }

    function addChatLine(message) {
        setChatLog(prev => [...prev, message]);
    }

    useEffect(() => {
        if (!user || wsRef.current) return;

        const socket = new WebSocket(`${WEBSOCKET_URL}/ws/${sessionId}`);

        socket.onopen = async () => {
            socket.send(JSON.stringify({
                type: "join",
                username: user.username,
                userID: user.id
            }));

            const sessionData = await getFullSessionData(sessionId, user.id);
            setState(sessionData["state"]);
            setGameData(sessionData.gameData);
        };

        socket.onmessage = (event) => {
            const data = JSON.parse(event.data);

            if (data.type === "chat") {
                addChatLine({ user: data.user, message: data.message });
            }

            if (data.type === "lobby_update") {
                setPlayers(data.players);
                setState(data.state);
                if (data.gameData) setGameData(data.gameData);
                if (data.cwd) setCwd(data.cwd);
                return;
            }

            if (data.type === "system") {
                addCommandLine(`[SYSTEM] ${data.message}`);
            }

            if (data.type === "command_output") {
                if (data.cwd) setCwd(data.cwd);
                data.stdout.forEach(line => addCommandLine(line));
                data.stderr.forEach(line => addCommandLine(line));
            }

            if (data.type === "background_job_complete") {
                addCommandLine(`[job ${data.job_id}] completed with status ${data.status}`);
                (data.stdout || []).forEach(line => addCommandLine(line));
                (data.stderr || []).forEach(line => addCommandLine(line));
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
        <SessionContext.Provider value={{ sessionId, wsRef, addCommandLine }}>
          <div className="game">
            <div className="sidebar-page">
                <div className="sidebar-nav">
                    {["General", "Settings", "Environment", "Chat"].map(tab => (
                        <button
                            key={tab}
                            type="button"
                            className={activeTab === tab ? "active" : ""}
                            aria-pressed={activeTab === tab}
                            onClick={() => handleTabSwitch(tab)}
                        >
                            {tab}
                        </button>
                    ))}
                </div>
                {activeTab === "General" && <GeneralTab />}
                {activeTab === "Settings" && <SettingsTab />}
                {activeTab === "Environment" && <EnvironmentTab />}
                {activeTab === "Chat" && <ChatTab wsRef={wsRef} chatLog={chatLog} username={user?.username} />}
            </div>

            <main className="game-stage">
                {state === "waiting" && <WaitingScreen players={players} canStart={String(gameData?.creatorID) === String(user?.id)} onGameStart={() => wsRef.current?.send(JSON.stringify({ type: "start_game" }))} />}
                {state === "running" && (
                    <Gamescreen
                        wsRef={wsRef}
                        commandLog={commandLog}
                        addCommandLine={addCommandLine}
                        username={user?.username}
                        cwd={cwd}
                    />
                )}
                {state === "starting" && <Versus players={players} />}
                {state === "finished" && <div className="game-finished"><h1>Game complete</h1></div>}
                {!state && <h1>Loading...</h1>}
            </main>
            {gameData && <GameDataPanel gameData={gameData} />}
          </div>
        </SessionContext.Provider>
    )
}

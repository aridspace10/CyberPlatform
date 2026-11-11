import { useEffect, useRef, useState } from "react";
import Gamescreen from "./Gamescreen";
import WaitingScreen from "./WaitingScreen";
import Versus from "./Versus";
import GameDataPanel from "./GameDataPanel";
import { useParams } from "react-router-dom";
import { useAuth } from "../auth/useAuth";
import { SessionContext } from "../components/SessionContext";
import GeneralTab from "../components/GeneralTab";
import EnvironmentTab from "../components/EnvironmentTab";
import SettingsTab from "../components/SettingsTab";
import ChatTab from "../components/ChatTab"
import { WEBSOCKET_URL } from "../api/config";
import { answerSessionRequest, getSessionAccess, getSessionRequests, requestSessionJoin } from "../api/sessions";
import "./Gamescreen.css"

export default function Game() {
    const { sessionId } = useParams();
    const { user, logout } = useAuth()
    const [players, setPlayers] = useState([]);
    const wsRef = useRef(null);
    const [commandLog, setCommandLog] = useState([]);
    const [chatLog, setChatLog] = useState([]);
    const [state, setState] = useState(null);
    const [gameData, setGameData] = useState(null);
    const [activeTab, setActiveTab] = useState("General");
    const [cwd, setCwd] = useState("/");
    const [access, setAccess] = useState(null);
    const [accessError, setAccessError] = useState("");
    const [joinAttempt, setJoinAttempt] = useState(0);
    const [joinRequests, setJoinRequests] = useState([]);
    const [inviteNotice, setInviteNotice] = useState("");

    function addCommandLine(text) {
        setCommandLog(prev => [...prev, text]);
    }

    function addChatLine(message) {
        setChatLog(prev => [...prev, message]);
    }

    useEffect(() => {
        if (!user || wsRef.current) return;

        const socket = new WebSocket(`${WEBSOCKET_URL}/ws/${sessionId}`);

        socket.onopen = () => {
            socket.send(JSON.stringify({
                type: "join",
                token: localStorage.getItem("token"),
            }));
        };

        socket.onmessage = (event) => {
            const data = JSON.parse(event.data);

            if (data.type === "chat" && typeof data.message === "string" && data.message.trim()) {
                addChatLine({
                    user: typeof data.user === "string" ? data.user : "Player",
                    message: data.message,
                });
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
                if (data.status !== undefined && data.status !== 0 &&
                    data.stdout.length === 0 && data.stderr.length === 0) {
                    addCommandLine(`[exit status ${data.status}: no output]`);
                }
            }

            if (data.type === "background_job_complete") {
                addCommandLine(`[job ${data.job_id}] completed with status ${data.status}`);
                (data.stdout || []).forEach(line => addCommandLine(line));
                (data.stderr || []).forEach(line => addCommandLine(line));
            }
        };

        socket.onclose = (event) => {
            if (event.code === 4401) logout();
            if (event.code === 4403) {
                getSessionAccess(sessionId).then(setAccess).catch(error => setAccessError(error.message));
            }
            if (event.code === 4404) setAccessError("Session not found");
        };

        wsRef.current = socket;

        return () => {
            socket.close();
            wsRef.current = null;
        };
    }, [user, sessionId, logout, joinAttempt]);

    useEffect(() => {
        if (state !== "waiting" || String(gameData?.creatorID) !== String(user?.id)) return;
        const refresh = () => getSessionRequests(sessionId)
            .then(data => setJoinRequests(data.requests))
            .catch(error => setAccessError(error.message));
        refresh();
        const timer = window.setInterval(refresh, 4000);
        return () => window.clearInterval(timer);
    }, [state, gameData?.creatorID, user?.id, sessionId]);

    const handleJoinRequest = async () => {
        try {
            await requestSessionJoin(sessionId);
            setAccess(previous => ({ ...previous, status: "pending" }));
            setAccessError("");
        } catch (error) {
            setAccessError(error.message);
        }
    };

    const handleRequestDecision = async (requesterId, decision) => {
        try {
            await answerSessionRequest(sessionId, requesterId, decision);
            setJoinRequests(current => current.filter(request => request.user_id !== requesterId));
            setAccessError("");
        } catch (error) {
            setAccessError(error.message);
        }
    };

    const handleCopyInvite = async () => {
        try {
            await navigator.clipboard.writeText(window.location.href);
            setInviteNotice("Invite link copied");
        } catch {
            setInviteNotice("Could not copy the link. Copy this page URL instead.");
        }
    };

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

            <main className={`game-stage${state === "waiting" || !state ? " game-stage-lobby" : ""}`}>
                {access && !state && <div className="session-access-panel">
                    <h1>{access.name}</h1>
                    {access.status === "requestable" && <>
                        <p>This private session requires host approval.</p>
                        <button onClick={handleJoinRequest}>Request to join</button>
                    </>}
                    {access.status === "pending" && <>
                        <p>Your request is waiting for host approval.</p>
                        <button onClick={() => setJoinAttempt(attempt => attempt + 1)}>Try joining again</button>
                    </>}
                    {access.status === "denied" && <p>You cannot join this session.</p>}
                </div>}
                {accessError && <p role="alert">{accessError}</p>}
                {inviteNotice && <p role="status">{inviteNotice}</p>}
                {state === "waiting" && <WaitingScreen players={players} canStart={String(gameData?.creatorID) === String(user?.id)} onGameStart={() => wsRef.current?.send(JSON.stringify({ type: "start_game" }))} />}
                {state === "waiting" && String(gameData?.creatorID) === String(user?.id) &&
                    <button className="copy-invite" onClick={handleCopyInvite}>Copy invite link</button>}
                {state === "waiting" && String(gameData?.creatorID) === String(user?.id) && joinRequests.length > 0 && <section className="session-requests">
                    <h2>Join requests</h2>
                    {joinRequests.map(request => <div key={request.user_id}>
                        <span>{request.username}</span>
                        <button onClick={() => handleRequestDecision(request.user_id, "accept")}>Accept</button>
                        <button onClick={() => handleRequestDecision(request.user_id, "decline")}>Decline</button>
                    </div>)}
                </section>}
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
                {!state && !access && !accessError && <h1>Loading...</h1>}
            </main>
            {gameData && <GameDataPanel gameData={gameData} />}
          </div>
        </SessionContext.Provider>
    )
}

import { useEffect, useRef, useState } from "react";
import Gamescreen from "./Gamescreen";
import WaitingScreen from "./WaitingScreen";
import Versus from "./Versus";
import GameDataPanel from "./GameDataPanel";
import { Link, useParams } from "react-router-dom";
import { useAuth } from "../auth/useAuth";
import { SessionContext } from "../components/SessionContext";
import GeneralTab from "../components/GeneralTab";
import EnvironmentTab from "../components/EnvironmentTab";
import SettingsTab from "../components/SettingsTab";
import ChatTab from "../components/ChatTab"
import { DEFAULT_SANDBOX_SETTINGS, loadSandboxSettings, saveSandboxSettings } from "./sandboxSettings";
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
    const [unreadChatCount, setUnreadChatCount] = useState(0);
    const [state, setState] = useState(null);
    const [gameData, setGameData] = useState(null);
    const [activeTab, setActiveTab] = useState("General");
    const [compactView, setCompactView] = useState("game");
    const [sandboxSettings, setSandboxSettings] = useState(() => loadSandboxSettings(user.id));
    const notificationRef = useRef({ activeTab, isSandbox: false, enabled: sandboxSettings.chatNotifications });
    const [cwd, setCwd] = useState("/");
    const [terminalInteraction, setTerminalInteraction] = useState(null);
    const [access, setAccess] = useState(null);
    const [accessError, setAccessError] = useState("");
    const [connectionConflict, setConnectionConflict] = useState(false);
    const [connectionStatus, setConnectionStatus] = useState("connecting");
    const [joinAttempt, setJoinAttempt] = useState(0);
    const [joinRequests, setJoinRequests] = useState([]);
    const [inviteNotice, setInviteNotice] = useState("");
    const [resetPending, setResetPending] = useState(false);
    const [resetError, setResetError] = useState("");
    const [terminalVersion, setTerminalVersion] = useState(0);
    const isSandbox = gameData?.isSandbox === true;
    const hasQuestionPanel = Boolean(gameData && !isSandbox && gameData.gameType !== "Tutorial");
    const visibleCompactView = compactView === "questions" && !hasQuestionPanel ? "game" : compactView;

    useEffect(() => {
        notificationRef.current = {
            activeTab,
            isSandbox,
            enabled: sandboxSettings.chatNotifications,
        };
    }, [activeTab, isSandbox, sandboxSettings.chatNotifications]);

    useEffect(() => {
        if (isSandbox) saveSandboxSettings(user.id, sandboxSettings);
    }, [isSandbox, sandboxSettings, user.id]);

    function addCommandLine(text) {
        setCommandLog(prev => [...prev, text]);
    }

    function addChatLine(message) {
        setChatLog(prev => [...prev, message]);
    }

    useEffect(() => {
        if (!user || wsRef.current) return;

        let disposed = false;
        const socket = new WebSocket(`${WEBSOCKET_URL}/ws/${sessionId}`);
        const connectionTimeout = window.setTimeout(() => {
            if (!disposed && socket.readyState !== WebSocket.CLOSED) socket.close();
        }, 10000);

        socket.onopen = () => {
            setConnectionConflict(false);
            setAccessError("");
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
                const notification = notificationRef.current;
                if (notification.isSandbox && notification.enabled && notification.activeTab !== "Chat") {
                    setUnreadChatCount(count => count + 1);
                }
            }

            if (data.type === "lobby_update") {
                window.clearTimeout(connectionTimeout);
                setConnectionStatus("connected");
                setPlayers(data.players);
                setState(data.state);
                setAccess(null);
                if (data.gameData) {
                    notificationRef.current.isSandbox = data.gameData.isSandbox === true;
                    setGameData(data.gameData);
                }
                if (data.cwd) setCwd(data.cwd);
                return;
            }

            if (data.type === "system") {
                addCommandLine(`[SYSTEM] ${data.message}`);
                if (data.message === `${user.username} joined session`) {
                    addCommandLine("[SYSTEM] Type 'help' to see available commands.");
                }
            }

            if (data.type === "sandbox_reset") {
                setResetPending(false);
                setResetError("");
                setCwd(data.cwd || "/");
                setCommandLog(["[SYSTEM] Sandbox reset to a basic environment."]);
                setTerminalVersion(version => version + 1);
            }

            if (data.type === "sandbox_reset_error") {
                setResetPending(false);
                setResetError(data.message || "Could not reset Sandbox. Please try again.");
            }

            if (data.type === "command_output") {
                if (data.cwd) setCwd(data.cwd);
                setTerminalInteraction(data.interaction?.mode === "foreground" ? data.interaction : null);
                data.stdout.forEach(line => addCommandLine(line));
                data.stderr.forEach(line => addCommandLine(line));
                if (data.status !== undefined && data.status !== 0 &&
                    data.stdout.length === 0 && data.stderr.length === 0) {
                    addCommandLine(`[exit status ${data.status}: no output]`);
                }
            }

            if (data.type === "terminal_state") {
                setTerminalInteraction(data.busy ? { mode: data.mode || "foreground", prompt: data.prompt || "" } : null);
            }

            if (data.type === "background_job_complete") {
                addCommandLine(`[job ${data.job_id}] completed with status ${data.status}`);
                (data.stdout || []).forEach(line => addCommandLine(line));
                (data.stderr || []).forEach(line => addCommandLine(line));
            }
        };

        socket.onclose = (event) => {
            if (disposed) return;
            window.clearTimeout(connectionTimeout);
            wsRef.current = null;
            setState(null);
            setPlayers([]);
            setGameData(null);
            setTerminalInteraction(null);
            setResetPending(false);
            setConnectionStatus([4401, 4403, 4404, 4409].includes(event.code) ? "rejected" : "disconnected");
            if (event.code === 4401) logout();
            if (event.code === 4403) {
                getSessionAccess(sessionId).then(setAccess).catch(error => setAccessError(error.message));
            }
            if (event.code === 4404) setAccessError("Session not found");
            if (event.code === 4409) {
                setState(null);
                setConnectionConflict(true);
                setAccessError("This session is already open in another tab. Close that tab, then try again.");
            }
        };

        wsRef.current = socket;

        return () => {
            disposed = true;
            window.clearTimeout(connectionTimeout);
            socket.close();
            if (wsRef.current === socket) wsRef.current = null;
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
        notificationRef.current.activeTab = tab;
        setActiveTab(tab);
        if (tab === "Chat") setUnreadChatCount(0);
    };

    const handleSandboxSettingChange = (key, value) => {
        if (key === "chatNotifications") notificationRef.current.enabled = value;
        setSandboxSettings(current => ({ ...current, [key]: value }));
        if (key === "chatNotifications" && !value) setUnreadChatCount(0);
    };

    const handleResetSandboxSettings = () => {
        notificationRef.current.enabled = DEFAULT_SANDBOX_SETTINGS.chatNotifications;
        setSandboxSettings({ ...DEFAULT_SANDBOX_SETTINGS });
    };

    const handleResetSandbox = () => {
        if (!window.confirm("Reset your Sandbox? This will permanently delete your files and shell changes and restore a basic environment.")) return;
        if (wsRef.current?.readyState !== WebSocket.OPEN) {
            setResetError("Not connected. Please reconnect before resetting your Sandbox.");
            return;
        }
        setResetError("");
        setResetPending(true);
        wsRef.current.send(JSON.stringify({ type: "reset_sandbox" }));
    };

    const handleReconnect = () => {
        setConnectionStatus("connecting");
        setConnectionConflict(false);
        setState(null);
        setPlayers([]);
        setGameData(null);
        setTerminalInteraction(null);
        setAccess(null);
        setAccessError("");
        setResetError("");
        setJoinAttempt(attempt => attempt + 1);
    };

    return (
        <SessionContext.Provider value={{ sessionId, wsRef, addCommandLine }}>
          <div
            className={`game${isSandbox ? " sandbox" : ""}${isSandbox && !sandboxSettings.wrapLines ? " sandbox-no-wrap" : ""}${isSandbox && sandboxSettings.highContrast ? " sandbox-high-contrast" : ""}${isSandbox && sandboxSettings.reducedMotion ? " sandbox-reduced-motion" : ""}`}
            style={isSandbox ? { "--sandbox-terminal-font-size": `${sandboxSettings.fontSize}px` } : undefined}
          >
            <header className="game-topbar">
                <Link className="game-topbar-brand" to="/" aria-label="CyberPlatform home"><span className="game-topbar-mark" aria-hidden="true">&gt;_</span><span>CYBER<span>PLATFORM</span></span></Link>
                <span className="game-topbar-label">{isSandbox ? "SANDBOX / TERMINAL" : "SESSION / TERMINAL"}</span>
                <nav className="game-topbar-links" aria-label="Site navigation">
                    <Link to="/">Home</Link>
                    <Link to="/sessions">Sessions</Link>
                    <Link to="/profile">Profile</Link>
                </nav>
            </header>
            <nav className="game-mobile-nav" aria-label="Game panels">
                <button type="button" aria-controls="game-stage" aria-pressed={visibleCompactView === "game"} onClick={() => setCompactView("game")}>Game</button>
                <button type="button" aria-controls="game-sidebar" aria-pressed={visibleCompactView === "sidebar"} onClick={() => setCompactView("sidebar")}>Session tabs</button>
                {hasQuestionPanel && <button type="button" aria-controls="game-questions" aria-pressed={visibleCompactView === "questions"} onClick={() => setCompactView("questions")}>Questions</button>}
            </nav>
            <div className={`game-workspace game-view-${visibleCompactView}`}>
            <div className="sidebar-page" id="game-sidebar">
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
                            {tab === "Chat" && isSandbox && unreadChatCount > 0 && sandboxSettings.chatNotifications &&
                                <span className="sidebar-tab-badge" aria-label={`${unreadChatCount} unread messages`}>{unreadChatCount > 99 ? "99+" : unreadChatCount}</span>}
                        </button>
                    ))}
                </div>
                {activeTab === "General" && <GeneralTab isSandbox={isSandbox} onResetSandbox={handleResetSandbox} resetPending={resetPending} resetError={resetError} />}
                {activeTab === "Settings" && <SettingsTab isSandbox={isSandbox} settings={sandboxSettings} onChange={handleSandboxSettingChange} onReset={handleResetSandboxSettings} />}
                {activeTab === "Environment" && <EnvironmentTab />}
                {activeTab === "Chat" && <ChatTab wsRef={wsRef} chatLog={chatLog} username={user?.username} />}
            </div>

            <main id="game-stage" className={`game-stage${state === "waiting" || !state ? " game-stage-lobby" : ""}`}>
                {access && !state && <div className="session-access-panel">
                    <h1>{access.name}</h1>
                    {access.status === "requestable" && <>
                        <p>This private session requires host approval.</p>
                        <button onClick={handleJoinRequest}>Request to join</button>
                    </>}
                    {access.status === "pending" && <>
                        <p>Your request is waiting for host approval.</p>
                        <button onClick={handleReconnect}>Try joining again</button>
                    </>}
                    {access.status === "denied" && <p>You cannot join this session.</p>}
                </div>}
                {accessError && <p role="alert">{accessError}</p>}
                {connectionStatus === "disconnected" && !accessError && !connectionConflict && <div className="session-connection-panel" role="alert">
                    <p>Connection lost. Your session may have changed while you were away.</p>
                    <button type="button" onClick={handleReconnect}>Reconnect to session</button>
                </div>}
                {connectionStatus === "connecting" && joinAttempt > 0 && <p role="status">Reconnecting to session...</p>}
                {connectionConflict && <button onClick={handleReconnect}>Try joining again</button>}
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
                        key={terminalVersion}
                        wsRef={wsRef}
                        commandLog={commandLog}
                        addCommandLine={addCommandLine}
                        username={user?.username}
                        cwd={cwd}
                        interaction={terminalInteraction}
                    />
                )}
                {state === "starting" && <Versus players={players} />}
                {state === "finished" && <div className="game-finished"><h1>Game complete</h1></div>}
                {!state && !access && !accessError && connectionStatus === "connecting" && <h1>Loading...</h1>}
            </main>
            {gameData && <GameDataPanel id="game-questions" gameData={gameData} />}
            </div>
          </div>
        </SessionContext.Provider>
    )
}

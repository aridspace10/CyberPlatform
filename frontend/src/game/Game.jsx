import { useEffect, useRef, useState } from "react";
import Gamescreen from "./Gamescreen";
import WaitingScreen from "./WaitingScreen";
import Versus from "./Versus";
import { useParams } from "react-router-dom";
import { useAuth } from "../auth/useAuth";
import { getFullSessionData } from "../api/sessions";
import { SessionContext } from "../components/SessionContext";

export default function Game() {
    const { sessionId } = useParams();
    const { user } = useAuth()
    const [players, setPlayers] = useState([]);
    const wsRef = useRef(null);
    const [log, setLog] = useState([]);
    const [state, setState] = useState("")
    const [interaction, setInteraction] = useState("")

    function addLine(text) {
        setLog(prev => [...prev, text]);
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
                addLine(`${data.user}: ${data.message}`);
            }

            if (data.type === "lobby_update") {
                setPlayers(data.players);
                setState(data.state);
                return;
            }

            if (data.type === "system") {
                addLine(`[SYSTEM] ${data.message}`);
            }

            if (data.type === "command_output") {
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
            }
        };

        wsRef.current = socket;

        return () => {
            socket.close();
            wsRef.current = null;
        };
    }, [user, sessionId]);

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

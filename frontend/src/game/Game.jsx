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
    const [state, setState] = useState("")

    function addCommandLine(text) {
        setCommandLog(prev => [...prev, text]);
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
                addCommandLine(`${data.user}: ${data.message}`);
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

    if (state == 'waiting') {
        return (<WaitingScreen players={players} />)
    } else if (state == 'running') {
        return (
            <SessionContext.Provider value={{ sessionId, wsRef }}>
                <Gamescreen wsRef={wsRef} log={log} addLine={addCommandLine} />
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
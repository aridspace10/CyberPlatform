import { useScroll } from "motion/react";
import { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router";
import Gamescreen from "./Gamescreen";
import WaitingScreen from "./WaitingScreen";

export default function Game() {
    const location = useLocation();
    const { sessionId } = location.state || {};
    const [sessionData, setSessionData] = useState(null);
    const [players, setPlayers] = useState([]);
    const [username, setUsername] = useState("");
    const wsRef = useRef(null);
    const hasPrompted = useRef(false);
    const [log, setLog] = useState([]);
    const [state, setState] = useState("")

    function addLine(text) {
        setLog(prev => [...prev, text]);
    }

    useEffect(() => {
        if (hasPrompted.current) return;
        hasPrompted.current = true;

        const name = prompt("Enter username");
        setUsername(name || "anonymous");
    }, []);

    useEffect(() => {
        if (!username) return;
        if (wsRef.current) return;

        const socket = new WebSocket(
            `ws://localhost:8000/ws/${sessionId}`
        );

        socket.onopen = () => {
            socket.send(JSON.stringify({
                type: "join",
                username: username
            }));
        }
        
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
                data.stdout.forEach(line => addLine(line));
                data.stderr.forEach(line => addLine(line));
            }
        };
        wsRef.current = socket;
        return () => {
            socket.close();
            wsRef.current = null;
        };
    }, [username]);

    if (state == 'waiting') {
        return (<WaitingScreen players={players} />)
    } else if (state == 'running') {
        return (<Gamescreen wsRef={wsRef} log={log} />)
    } else {
        return (
            <h1> Loading... </h1>
        )
    }
}
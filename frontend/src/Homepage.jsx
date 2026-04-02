import SessionList from "./components/SessionsList"
import "./Homepage.css"
import { Link, useNavigate } from 'react-router-dom';
import { useRef } from "react";
import { enterTutorial } from "./api/sessions";
import { useAuth } from "./auth/useAuth";

export default function Homepage() {
    const navigate = useNavigate();
    const nextId = useRef(123);
    const { user, logout } = useAuth();
    const handleSessionCreation = () => {
        const id = nextId.current++;
        navigate(`/game`, {state: {sessionId: id}});
    }

    const handleEnterSandbox = async () => {
        if (user == null) {
            navigate(`login`)
        }
        const data = await enterTutorial(user.id);
        console.log(data)
        navigate(`/sandbox/${data["session_id"]}`)
    }

    return (
        <div className="homepage">
            <h1> Hello </h1>
            <SessionList />
            <br></br>
            <button onClick={handleSessionCreation}> Create a new session </button>
            <button onClick={handleEnterSandbox}> Enter Sandbox </button>
            <button onClick={logout}> Log out</button>
        </div>
    )
}
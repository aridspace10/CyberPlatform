import SessionList from "./components/SessionsList"
import "./Homepage.css"
import { Link, useNavigate } from 'react-router-dom';
import { useRef } from "react";

export default function Homepage() {
    const navigate = useNavigate();
    const nextId = useRef(123);
    const handleSessionCreation = () => {
        const id = nextId.current++;
        navigate(`/game`, {state: {sessionId: id}});
    }

    return (
        <div className="homepage">
            <h1> Hello </h1>
            <SessionList />
            <br></br>
            <button onClick={handleSessionCreation}> Create a new session </button>
        </div>
    )
}
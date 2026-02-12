import SessionList from "./components/SessionsList"
import "./Homepage.css"
import { Link, useNavigate } from 'react-router-dom';

export default function Homepage() {
    const navigate = useNavigate();
    let nextid = 123
    const handleSessionCreation = () => {
        navigate(`/game`, {state: {sessionId: nextid++}});
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
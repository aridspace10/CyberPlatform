import SessionList from "./components/SessionsList"
import "./Homepage.css"
import { Link, useNavigate } from 'react-router-dom';
import { enterTutorial } from "./api/sessions";
import { useAuth } from "./auth/useAuth";

export default function Homepage() {
    const navigate = useNavigate();
    const { user, logout } = useAuth();
    const handleSessionCreation = () => {
        navigate("/session-create")
    }

    const handleEnterSandbox = async () => {
        if (user == null) {
            navigate(`login`)
        }
        const data = await enterTutorial(user.id);
        navigate(`/game/${data["session_id"]}`)
    }

    return (
        <div className="homepage">
            <h1> Hello </h1>
            <SessionList />
            {user && <Link to="/profile">Profile &amp; Friends</Link>}
            <br></br>
            <button onClick={handleSessionCreation}> Create a new session </button>
            <button onClick={handleEnterSandbox}> Enter Sandbox </button>
            <button onClick={logout}> Log out</button>
        </div>
    )
}

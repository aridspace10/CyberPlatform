import { useState } from "react";
import SessionList from "./components/SessionsList"
import "./Homepage.css"
import { Link, useNavigate } from 'react-router-dom';
import { enterTutorial } from "./api/sessions";
import { useAuth } from "./auth/useAuth";

export default function Homepage() {
    const navigate = useNavigate();
    const { user, logout } = useAuth();
    const [sandboxError, setSandboxError] = useState("");
    const [enteringSandbox, setEnteringSandbox] = useState(false);
    const handleSessionCreation = () => {
        navigate("/session-create")
    }

    const handleEnterSandbox = async () => {
        if (user == null) {
            navigate("/login");
            return;
        }
        setSandboxError("");
        setEnteringSandbox(true);
        try {
            const data = await enterTutorial(user.id);
            navigate(`/game/${data.session_id}`);
        } catch (error) {
            setSandboxError(error.message || "Could not enter Sandbox. Please try again");
        } finally {
            setEnteringSandbox(false);
        }
    }

    return (
        <div className="homepage">
            <h1> Hello </h1>
            <SessionList />
            {user && <Link to="/profile">Profile &amp; Friends</Link>}
            <br></br>
            <button onClick={handleSessionCreation}> Create a new session </button>
            {sandboxError && <p role="alert">{sandboxError}</p>}
            <button onClick={handleEnterSandbox} disabled={enteringSandbox}>
                {enteringSandbox ? "Entering Sandbox..." : "Enter Sandbox"}
            </button>
            <button onClick={logout}> Log out</button>
        </div>
    )
}

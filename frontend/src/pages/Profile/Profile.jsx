import { useState } from "react";
import { useAuth } from "../../auth/useAuth";
import "./Profile.css"

export default function Profile() {
    const { user } = useAuth();
    const [username, setUsername] = useState(user?.username ?? "");
    const [password, setPassword] = useState("");

    return (
        <div className="profile-page">
            <h1> Profile </h1>
            <input value={username} onChange={e => setUsername(e.target.value)} />
            <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
            />
        </div>
    )
}

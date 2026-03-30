import { useState } from "react";
import { useAuth } from "../auth/useAuth";
import "Profile.css"

export default function Profile() {
    return (
        <div className="profile-page">
            <h1> Profile </h1>
            <input onChange={e => setUsername(e.target.value)} />
            <input type="password" onChange={e => setPassword(e.target.value)} />
        </div>
    )
}
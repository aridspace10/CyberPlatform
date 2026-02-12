import { motion } from "motion/react"
import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router";
export default function WaitingScreen({players}) {
    const location = useLocation();
    const navigate = useNavigate();
    const { sessionId } = location.state || {};
    const handleStart = async () => {
        await fetch(`http://localhost:8000/api/sessions/${sessionId}/state`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ state: "running" })
        });
        navigate(`/game`, {state: {sessionId: sessionId}});
    }

    return (
        <div>
            <div className="players">
                {players.map(player => (
                    <motion.button
                        key={player}
                        initial={{ opacity: 0, scale: 0 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{
                            duration: 0.4,
                            scale: { type: "spring", visualDuration: 0.4, bounce: 0.5 },
                        }}
                    >
                        {player}
                    </motion.button>
                ))}
            </div>
            <div className="start-btn">
                
            </div>
        </div>
    )
}
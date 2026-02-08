import { motion } from "motion/react"
import { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router";
export default function WaitingScreen() {
    const players = ["PlayerA", "PlayerB"]

    const handleStart = () => {
        navigate(`/game`, {state: {sessionId: sessionId}});
    }

    return (
        <div>
            <div className="players">
                {players.map(player => 
                    <motion.button
                        initial={{ opacity: 0, scale: 0 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{
                            duration: 0.4,
                            scale: { type: "spring", visualDuration: 0.4, bounce: 0.5 },
                        }}
                    />
                )}
            </div>
            <div className="start-btn">
                
            </div>
        </div>
    )
}
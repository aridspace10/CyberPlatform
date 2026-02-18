import { motion } from "motion/react"
import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router";
import './WaitingScreen.css'
export default function WaitingScreen({players, onGameStart}) {
    const location = useLocation();
    const navigate = useNavigate();
    const { sessionId } = location.state || {};
    return (
        <div>
            <div className="players">
                {players.map(player => (
                    <motion.button
                        className="player"
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
            <div>
                <motion.button onClick={onGameStart} className="start-btn"> Start the game </motion.button>
            </div>
        </div>
    )
}
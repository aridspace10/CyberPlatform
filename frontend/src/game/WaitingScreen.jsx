import { motion as Motion } from "motion/react"
import './WaitingScreen.css'
export default function WaitingScreen({players, onGameStart, canStart}) {
    return (
        <div>
            <div className="players">
                {players.map(player => (
                    <Motion.button
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
                    </Motion.button>
                ))}
            </div>
            <div>
                {canStart && <Motion.button onClick={onGameStart} className="start-btn" disabled={players.length < 2}> Start the game </Motion.button>}
                {players.length < 2 && <p>Waiting for another player to join.</p>}
            </div>
        </div>
    )
}

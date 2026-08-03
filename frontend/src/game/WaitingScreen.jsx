import { motion as Motion } from "motion/react"
import './WaitingScreen.css'
export default function WaitingScreen({players, onGameStart}) {
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
                <Motion.button onClick={onGameStart} className="start-btn"> Start the game </Motion.button>
            </div>
        </div>
    )
}

import { motion as Motion, AnimatePresence } from "framer-motion";
import "./Versus.css"

export default function Versus({ players }) {

  return (
    <div className="arena">
      <Motion.div
        className="player-card"
        animate={"centerLeft"}
        variants={{
          start: { x: -200 },
          centerLeft: { x: -60 }
        }}
        transition={{ type: "spring", stiffness: 120, damping: 18 }}
      >
        {players[0]}
      </Motion.div>

      <AnimatePresence>
          <Motion.h1
            className="vs"
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0 }}
            transition={{ duration: 0.4, ease: "easeOut" }}
          >
            VS
          </Motion.h1>
      </AnimatePresence>

      <Motion.div
        className="player-card"
        animate={"start"}
        variants={{
          start: { x: 200 },
          centerRight: { x: 60 }
        }}
        transition={{ type: "spring", stiffness: 120, damping: 18 }}
      >
        {players[1]}
      </Motion.div>
    </div>
  );
}

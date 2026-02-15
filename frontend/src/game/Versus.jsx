import { motion, AnimatePresence } from "framer-motion";

export default function Versus({ players }) {
  const [matchStarting, setMatchStarting] = useState(false);

  return (
    <div className="arena">
      <motion.div
        className="player-card"
        animate={matchStarting ? "centerLeft" : "start"}
        variants={{
          start: { x: -200 },
          centerLeft: { x: -60 }
        }}
        transition={{ type: "spring", stiffness: 120, damping: 18 }}
      >
        {players[0]}
      </motion.div>

      <AnimatePresence>
        {matchStarting && (
          <motion.h1
            className="vs"
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0 }}
            transition={{ duration: 0.4, ease: "easeOut" }}
          >
            VS
          </motion.h1>
        )}
      </AnimatePresence>

      <motion.div
        className="player-card"
        animate={matchStarting ? "centerRight" : "start"}
        variants={{
          start: { x: 200 },
          centerRight: { x: 60 }
        }}
        transition={{ type: "spring", stiffness: 120, damping: 18 }}
      >
        {players[1]}
      </motion.div>

      {/* Dev trigger */}
      <button
        style={{ position: "absolute", bottom: 40 }}
        onClick={() => setMatchStarting(true)}
      >
        Start Match
      </button>
    </div>
  );
}

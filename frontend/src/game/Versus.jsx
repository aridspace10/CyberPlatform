import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import "./Versus.css"

export default function Versus({ players }) {

  return (
    <div className="arena">
      <motion.div
        className="player-card"
        animate={"centerLeft"}
        variants={{
          start: { x: -200 },
          centerLeft: { x: -60 }
        }}
        transition={{ type: "spring", stiffness: 120, damping: 18 }}
      >
        {players[0]}
      </motion.div>

      <AnimatePresence>
          <motion.h1
            className="vs"
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0 }}
            transition={{ duration: 0.4, ease: "easeOut" }}
          >
            VS
          </motion.h1>
      </AnimatePresence>

      <motion.div
        className="player-card"
        animate={"start"}
        variants={{
          start: { x: 200 },
          centerRight: { x: 60 }
        }}
        transition={{ type: "spring", stiffness: 120, damping: 18 }}
      >
        {players[1]}
      </motion.div>
    </div>
  );
}

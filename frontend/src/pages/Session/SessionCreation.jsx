import { useEffect, useRef, useState } from "react";
export default function SessionCreation() {
    const [name, setName] = useState("");
    const [playType, setPlayType] = useState("");
    const [allowPipes, setAllowPipes] = useState(false)

    const typeOptions = ["SinglePlayer", "Versus"]
    const commands = {
        "grep": ["Case Insensitive", "Find By Filename", "Match By Line", "Match By Word", "Show Line Number"],
        "sed":  ["Save a backup", "Case Insensitive"]
    }

    return (
        <div className="session-create-page">
            <h1> Create a new session </h1>
            <div className="create-left-side">
                <input
                    type="text"
                    placeholder="Name"
                    value={name}
                    onChange={e => setName(e.target.value)}
                    spellCheck={false}
                />
                <select value={value} onChange={e => setPlayType(e.target.value)}>
                    {typeOptions.map(opt => (
                        <option key={opt} value={opt}>
                        {opt}
                        </option>
                    ))}
                </select>
                <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
                    <Switch on={allowPipes} onChange={setAllowPipes} />
                    <span>{on ? "On" : "Off"}</span>
                </label>
            </div>
            <div className="create-right-side">
                <h1> Allowed Commands </h1>
                <div className="command-options">
                    <button> Select All </button>
                    <button> Deselect All </button>
                </div>
                <div className="commands">
                    {commands.map(command => 
                        <div className="command">
                            <h1> command </h1> 
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
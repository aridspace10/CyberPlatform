import { useEffect, useRef, useState } from "react";

export default function SessionCreation() {
    const [name, setName] = useState("");
    const [playType, setPlayType] = useState("SinglePlayer");
    const [allowPipes, setAllowPipes] = useState(false);
 
    const typeOptions = ["SinglePlayer", "Versus"];
    const commands = {
        grep: ["Case Insensitive", "Find By Filename", "Match By Line", "Match By Word", "Show Line Number"],
        sed:  ["Save a backup", "Case Insensitive"],
    };
 
    return (
        <div className="session-create-page">
            <h1 className="page-title">Create a New Session</h1>
            <div className="session-layout">
                <div className="create-left-side">
                    <h2 className="section-title">Session Info</h2>
 
                    <label className="field-label">Name</label>
                    <input
                        type="text"
                        className="text-input"
                        placeholder="Session name..."
                        value={name}
                        onChange={e => setName(e.target.value)}
                        spellCheck={false}
                    />
 
                    <label className="field-label">Play Type</label>
                    <select
                        className="select-input"
                        value={playType}
                        onChange={e => setPlayType(e.target.value)}
                    >
                        {typeOptions.map(opt => (
                            <option key={opt} value={opt}>{opt}</option>
                        ))}
                    </select>
 
                    <label className="field-label">Allow Pipes</label>
                    <label className="switch-row">
                        <Switch on={allowPipes} onChange={setAllowPipes} />
                        <span className="switch-label">{allowPipes ? "On" : "Off"}</span>
                    </label>
 
                    <button className="submit-btn">Create Session</button>
                </div>
 
                <div className="create-right-side">
                    <div className="right-header">
                        <h2 className="section-title">Allowed Commands</h2>
                        <div className="bulk-actions">
                            <button className="ghost-btn">Select All</button>
                            <button className="ghost-btn">Deselect All</button>
                        </div>
                    </div>
                    <div className="commands-list">
                        {Object.entries(commands).map(([command, options]) => (
                            <CommandBlock key={command} command={command} options={options} />
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}
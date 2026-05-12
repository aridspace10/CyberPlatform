import { useState } from "react";
import "./SessionCreation.css"
import { useAuth } from "../../auth/useAuth";
import Switch from "../../components/Switch";
import CommandBlock from "../../components/CommandBlock";
import NumberSelector from "../../components/NumberSelector";

export default function SessionCreation() {
    const [name, setName] = useState("");
    const [playType, setPlayType] = useState("SinglePlayer");
    const [gameType, setGameType] = useState("MiniGames");
    const [allowPipes, setAllowPipes] = useState(false);
    const [commandStates, setCommandStates] = useState({});
    const [rounds, setRounds] = useState(5);
    const { user } = useAuth()

    const typeOptions = ["SinglePlayer", "Versus"];
    const gameOptions = ["MiniGames"]
    const commands = {
        grep: ["Case Insensitive", "Find By Filename", "Match By Line", "Match By Word", "Show Line Number"],
        sed:  ["Save a backup", "Case Insensitive"],
    };

    const getCommandState = (cmd) => commandStates[cmd] || { selected: false, options: [] };

    const handleCommandToggle = (cmd, options) => {
        const current = getCommandState(cmd);
        if (current.selected) {
            setCommandStates(prev => ({ ...prev, [cmd]: { selected: false, options: [] } }));
        } else {
            setCommandStates(prev => ({ ...prev, [cmd]: { selected: true, options: [...options] } }));
        }
    };

    const handleOptionToggle = (cmd, opt) => {
        setCommandStates(prev => {
            const current = prev[cmd] || { selected: true, options: [] };
            const hasOpt = current.options.includes(opt);
            return {
                ...prev,
                [cmd]: {
                    ...current,
                    options: hasOpt
                        ? current.options.filter(o => o !== opt)
                        : [...current.options, opt],
                },
            };
        });
    };

    const handleSelectAll = () => {
        const next = {};
        Object.entries(commands).forEach(([cmd, opts]) => {
            next[cmd] = { selected: true, options: [...opts] };
        });
        setCommandStates(next);
    };

    const handleCreate = async () => {
        const config = {
            "name": name,
            "playType": playType,
            "gameType": gameType,
            "creatorID": user.id,
            "commands": commandStates,
            "options": {
                "allowPipes": allowPipes,
                "rounds": rounds,
            }
        }

        const res = await fetch(`http://localhost:8000/api/session_create`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ config })
        });

        const data = await res.json();
        return data
    }

    const handleDeselectAll = () => setCommandStates({});

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

                    <label className="field-label">Game Type</label>
                    <select
                        className="select-input"
                        value={gameType}
                        onChange={e => setGameType(e.target.value)}
                    >
                        {gameOptions.map(opt => (
                            <option key={opt} value={opt}>{opt}</option>
                        ))}
                    </select>

                    <button className="submit-btn" onClick={handleCreate}>Create Session</button>
                </div>

                <div className="create-right-side">
                    <div className="right-header">
                        <h2 className="section-title">General MiniGames Rules</h2>
                    </div>

                    <div className="rules-grid">
                        <NumberSelector
                            label="Rounds"
                            value={rounds}
                            onChange={setRounds}
                            min={1}
                            max={20}
                        />
                        <div className="inline-field">
                            <span className="field-label">Allow Pipes</span>
                            <label className="switch-row">
                                <Switch on={allowPipes} onChange={setAllowPipes} />
                                <span className="switch-label">{allowPipes ? "On" : "Off"}</span>
                            </label>
                        </div>
                        {/* more rule options can be added here */}
                    </div>

                    <hr className="section-divider" />

                    <div className="right-header">
                        <h2 className="section-title">Command Pool</h2>
                        <div className="bulk-actions">
                            <button className="ghost-btn" onClick={handleSelectAll}>Select All</button>
                            <button className="ghost-btn" onClick={handleDeselectAll}>Deselect All</button>
                        </div>
                    </div>
                    <div className="commands-list">
                        {Object.entries(commands).map(([command, options]) => {
                            const state = getCommandState(command);
                            return (
                                <CommandBlock
                                    key={command}
                                    command={command}
                                    options={options}
                                    commandSelected={state.selected}
                                    onCommandToggle={handleCommandToggle}
                                    selectedOptions={state.options}
                                    onOptionToggle={handleOptionToggle}
                                />
                            );
                        })}
                    </div>
                </div>
            </div>
        </div>
    );
}
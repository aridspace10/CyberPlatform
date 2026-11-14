import { useState } from "react";
import { useNavigate } from "react-router-dom";
import "./SessionCreation.css"
import { createSession } from "../../api/sessions";
import { useAuth } from "../../auth/useAuth";
import Switch from "../../components/Switch";
import CommandBlock from "../../components/CommandBlock";
import NumberSelector from "../../components/NumberSelector";

export default function SessionCreation() {
    const [name, setName] = useState("");
    const [playType, setPlayType] = useState("SinglePlayer");
    const [visibility, setVisibility] = useState("public");
    const [gameType, setGameType] = useState("MiniGames");
    const [allowPipes, setAllowPipes] = useState(false);
    const [commandStates, setCommandStates] = useState({ grep: { selected: true, options: [] } });
    const [rounds, setRounds] = useState(1);
    const [questionCount, setQuestionCount] = useState(10);
    const [timeLimitMinutes, setTimeLimitMinutes] = useState(5);
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState("");
    const { user, logout } = useAuth()
    const navigate = useNavigate();

    const typeOptions = ["SinglePlayer", "Versus"];
    const gameOptions = ["MiniGames"]
    const selectedCommandCount = Object.values(commandStates).filter(state => state.selected).length;
    const commands = {
        grep: [
            "Case Insensitive", "Find By Filename", "Match By Line", "Match By Word",
            "Show Line Number", "Invert Match", "Count Matches", "Only Matching Text",
            "Recursive Search", "Show Filename", "Hide Filename", "Explicit Pattern",
            "Include Files", "Exclude Files", "Exclude Directories", "Regular Expression",
        ],
        sed: [
            "Save a backup", "Case Insensitive", "Replace All", "Replace Occurrence",
            "Print Changes", "Quiet Output", "Expression Option", "Script File",
            "Edit In Place", "Line Address", "Pattern Address", "Last Line Address",
            "Address Range", "Negated Address", "Delete Lines", "Print Lines",
            "Multiple Expressions", "Alternate Delimiter", "Regex Substitution",
        ],
    };

    const getCommandState = (cmd) => commandStates[cmd] || { selected: false, options: [] };

    const handleCommandToggle = (cmd) => {
        const current = getCommandState(cmd);
        if (current.selected) {
            setCommandStates(prev => ({ ...prev, [cmd]: { selected: false, options: [] } }));
        } else {
            setCommandStates(prev => ({ ...prev, [cmd]: { selected: true, options: [] } }));
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

    const handleToggleAllCommandOptions = (cmd, options) => {
        setCommandStates(prev => {
            const current = prev[cmd] || { selected: false, options: [] };
            const allSelected = current.selected && options.every(opt => current.options.includes(opt));
            return {
                ...prev,
                [cmd]: {
                    selected: true,
                    options: allSelected ? [] : [...options],
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
        if (!Number.isInteger(user?.id)) {
            logout();
            return;
        }
        if (!name.trim()) {
            setError("Enter a session name");
            return;
        }
        if (!selectedCommandCount) {
            setError("Select at least one command");
            return;
        }
        if (questionCount < selectedCommandCount) {
            setError("Add at least one question per selected command");
            return;
        }

        const config = {
            "name": name.trim(),
            "playType": playType,
            "visibility": visibility,
            "gameType": gameType,
            "commands": commandStates,
            "options": {
                "allowPipes": allowPipes,
                "rounds": rounds,
                "questionCount": questionCount,
                "timeLimitSeconds": timeLimitMinutes * 60,
            }
        }

        setSubmitting(true);
        setError("");
        try {
            const data = await createSession(config);
            navigate(`/game/${data.session_id}`);
        } catch (err) {
            setError(err.message);
        } finally {
            setSubmitting(false);
        }
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

                    <label className="field-label" htmlFor="session-visibility">Session Type</label>
                    <select
                        id="session-visibility"
                        className="select-input"
                        value={visibility}
                        onChange={e => setVisibility(e.target.value)}
                    >
                        <option value="public">Public</option>
                        <option value="private">Private</option>
                        <option value="friends_only">Friends Only</option>
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

                    {error && <p className="session-create-error" role="alert">{error}</p>}
                    <button className="submit-btn" onClick={handleCreate} disabled={submitting}>
                        {submitting ? "Creating..." : "Create Session"}
                    </button>
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
                        <NumberSelector
                            label="Questions per round"
                            value={questionCount}
                            onChange={setQuestionCount}
                            min={Math.max(1, selectedCommandCount)}
                            max={50}
                        />
                        {playType === "Versus" && <NumberSelector
                            label="Minutes per round"
                            value={timeLimitMinutes}
                            onChange={setTimeLimitMinutes}
                            min={1}
                            max={60}
                        />}
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
                                    onToggleAllOptions={handleToggleAllCommandOptions}
                                />
                            );
                        })}
                    </div>
                </div>
            </div>
        </div>
    );
}

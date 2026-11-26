import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { createSession } from "../../api/sessions";
import { useAuth } from "../../auth/useAuth";
import CommandBlock from "../../components/CommandBlock";
import NumberSelector from "../../components/NumberSelector";
import { COMMANDS, commandOptions } from "./commandOptions";
import "./SessionCreation.css";

const emptySelection = { selected: false, options: [] };
const commandNames = Object.keys(COMMANDS);

export default function SessionCreation() {
    const [name, setName] = useState("");
    const [playType, setPlayType] = useState("Versus");
    const [visibility, setVisibility] = useState("public");
    const [allowPipes, setAllowPipes] = useState(false);
    const [commandStates, setCommandStates] = useState({ grep: { selected: true, options: [] } });
    const [rounds, setRounds] = useState(1);
    const [questionCount, setQuestionCount] = useState(10);
    const [timeLimitMinutes, setTimeLimitMinutes] = useState(5);
    const [submitting, setSubmitting] = useState(false);
    const [errors, setErrors] = useState({});
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    const nameRef = useRef(null);
    const commandsRef = useRef(null);

    const getState = command => commandStates[command] || emptySelection;
    const selectedCommands = commandNames.filter(command => getState(command).selected);
    const selectedModes = selectedCommands.reduce((count, command) => count + getState(command).options.length, 0);
    const basicCommands = selectedCommands.filter(command => !getState(command).options.length);
    const visibilityText = { public: "Anyone can find and join.", private: "Players request access before joining.", friends_only: "Only your friends can find and join." };

    const clearError = key => setErrors(previous => {
        if (!previous[key]) return previous;
        const next = { ...previous };
        delete next[key];
        delete next.submit;
        return next;
    });

    const toggleCommand = command => {
        setCommandStates(previous => {
            const current = previous[command] || emptySelection;
            return { ...previous, [command]: { ...current, selected: !current.selected } };
        });
        clearError("commands");
    };

    const toggleOption = (command, option) => {
        setCommandStates(previous => {
            const current = previous[command];
            return { ...previous, [command]: {
                ...current,
                options: current.options.includes(option)
                    ? current.options.filter(value => value !== option)
                    : [...current.options, option],
            } };
        });
        clearError("commands");
    };

    const toggleAllOptions = (command, options) => {
        setCommandStates(previous => {
            const current = previous[command];
            const allSelected = options.every(option => current.options.includes(option));
            return { ...previous, [command]: { ...current, options: allSelected ? [] : [...options] } };
        });
        clearError("commands");
    };

    const setAllCommands = selected => {
        setCommandStates(previous => Object.fromEntries(commandNames.map(command => [
            command, { ...(previous[command] || emptySelection), selected },
        ])));
        clearError("commands");
    };

    const handleCreate = async event => {
        event.preventDefault();
        if (submitting) return;
        if (!Number.isInteger(user?.id)) {
            logout();
            return;
        }
        const nextErrors = {};
        if (!name.trim()) nextErrors.name = "Enter a session name.";
        else if (name.trim().length > 100) nextErrors.name = "Use 100 characters or fewer.";
        if (!selectedCommands.length) nextErrors.commands = "Select at least one command.";
        if (!Number.isInteger(rounds) || rounds < 1 || rounds > 20) nextErrors.rounds = "Choose 1 to 20 rounds.";
        if (!Number.isInteger(questionCount) || questionCount < 1 || questionCount > 50) nextErrors.questionCount = "Choose 1 to 50 questions.";
        if (playType === "Versus" && (!Number.isInteger(timeLimitMinutes) || timeLimitMinutes < 1 || timeLimitMinutes > 60)) nextErrors.timeLimit = "Choose 1 to 60 minutes.";
        if (Object.keys(nextErrors).length) {
            setErrors(nextErrors);
            if (nextErrors.name) nameRef.current?.focus();
            else if (nextErrors.commands) commandsRef.current?.focus();
            return;
        }

        const config = {
            name: name.trim(),
            playType,
            visibility: playType === "SinglePlayer" ? "private" : visibility,
            gameType: "MiniGames",
            commands: commandStates,
            options: { allowPipes, rounds, questionCount, timeLimitSeconds: timeLimitMinutes * 60 },
        };
        setSubmitting(true);
        setErrors({});
        try {
            const data = await createSession(config);
            navigate(`/game/${data.session_id}`);
        } catch (error) {
            const message = error instanceof TypeError ? "Could not reach the server. Try again." : error?.message || "Could not create the session. Try again.";
            const key = /name/i.test(message) ? "name" : /command|option|mode/i.test(message) ? "commands" : /question/i.test(message) ? "questionCount" : /round/i.test(message) ? "rounds" : /time|minute/i.test(message) ? "timeLimit" : "submit";
            setErrors({ [key]: message });
        } finally {
            setSubmitting(false);
        }
    };

    return <main className="session-create-page">
        <header className="session-page-header">
            <p className="session-eyebrow">MiniGames</p>
            <h1 className="page-title">Create a session</h1>
            <p>Set the rules, then choose which commands and question modes can appear.</p>
        </header>
        <form onSubmit={handleCreate} noValidate>
            <div className="session-layout">
                <section className="session-card session-basics" aria-labelledby="session-details-heading">
                    <h2 id="session-details-heading">1. Session details</h2>
                    <div className="session-field">
                        <label htmlFor="session-name">Session name</label>
                        <input id="session-name" ref={nameRef} type="text" value={name} onChange={event => { setName(event.target.value); clearError("name"); }} maxLength={101} aria-invalid={!!errors.name} aria-describedby={errors.name ? "session-name-error" : undefined} placeholder="Give your session a name" />
                        {errors.name && <p id="session-name-error" className="session-create-error" role="alert">{errors.name}</p>}
                    </div>
                    <div className="session-field">
                        <label htmlFor="session-play-type">Play type</label>
                        <select id="session-play-type" value={playType} onChange={event => setPlayType(event.target.value)}>
                            <option value="Versus">Versus · two players</option>
                            <option value="SinglePlayer">Single player · play alone</option>
                        </select>
                        <p className="session-field-help">{playType === "Versus" ? "The session waits for a second player before play begins." : "Starts immediately and is private to you. There is no round timer."}</p>
                    </div>
                    {playType === "Versus" && <div className="session-field">
                        <label htmlFor="session-visibility">Who can join?</label>
                        <select id="session-visibility" value={visibility} onChange={event => setVisibility(event.target.value)}>
                            <option value="public">Public</option>
                            <option value="friends_only">Friends only</option>
                            <option value="private">Private · approval required</option>
                        </select>
                        <p className="session-field-help">{visibilityText[visibility]}</p>
                    </div>}
                    <p className="session-fixed-game">Game type <strong>MiniGames</strong></p>
                </section>

                <section className="session-card session-rules" aria-labelledby="session-rules-heading">
                    <h2 id="session-rules-heading">2. Round rules</h2>
                    <div className="rules-grid">
                        <div><NumberSelector id="session-rounds" label="Rounds" value={rounds} onChange={value => { setRounds(value); clearError("rounds"); }} min={1} max={20} invalid={!!errors.rounds} describedBy={errors.rounds ? "rounds-error" : undefined} />{errors.rounds && <p id="rounds-error" className="session-create-error" role="alert">{errors.rounds}</p>}</div>
                        <div><NumberSelector id="session-questions" label="Questions per round" value={questionCount} onChange={value => { setQuestionCount(value); clearError("questionCount"); }} min={1} max={50} invalid={!!errors.questionCount} describedBy={errors.questionCount ? "questions-help questions-error" : "questions-help"} /><p id="questions-help" className="session-field-help">Each round draws this many questions from your selected commands and modes.</p>{errors.questionCount && <p id="questions-error" className="session-create-error" role="alert">{errors.questionCount}</p>}</div>
                        {playType === "Versus" && <div><NumberSelector id="session-time" label="Minutes per round" value={timeLimitMinutes} onChange={value => { setTimeLimitMinutes(value); clearError("timeLimit"); }} min={1} max={60} invalid={!!errors.timeLimit} describedBy={errors.timeLimit ? "time-error" : undefined} /><p className="session-field-help">Timer applies to Versus rounds.</p>{errors.timeLimit && <p id="time-error" className="session-create-error" role="alert">{errors.timeLimit}</p>}</div>}
                    </div>
                    <label className="pipes-choice"><input type="checkbox" checked={allowPipes} onChange={event => setAllowPipes(event.target.checked)} /><span><strong>Allow pipes</strong><small>Let players chain commands with |.</small></span></label>
                </section>

                <section className="session-card session-commands" aria-labelledby="session-commands-heading">
                    <div className="command-section-heading">
                        <div><h2 id="session-commands-heading" ref={commandsRef} tabIndex={-1}>3. Command pool</h2><p>Choose commands to make available in the terminal. Expand each command to choose its question modes.</p></div>
                        <div className="bulk-actions"><button type="button" onClick={() => setAllCommands(true)}>Select all commands</button><button type="button" onClick={() => setAllCommands(false)}>Clear all commands</button></div>
                    </div>
                    <p className="pool-count" aria-live="polite">{selectedCommands.length}/{commandNames.length} commands selected · {selectedModes} selected modes</p>
                    <p className="session-field-help">A command with no selected modes gives basic questions. Selected modes form a pool, so a round may use only some of them.</p>
                    {errors.commands && <p className="session-create-error" role="alert">{errors.commands}</p>}
                    <div className="commands-list">{commandNames.map(command => {
                        const state = getState(command);
                        return <CommandBlock key={command} command={command} description={COMMANDS[command].description} groups={COMMANDS[command].groups} options={commandOptions(command)} commandSelected={state.selected} selectedOptions={state.options} onCommandToggle={toggleCommand} onOptionToggle={toggleOption} onToggleAllOptions={toggleAllOptions} />;
                    })}</div>
                </section>
            </div>
            <section className="session-card session-summary" aria-labelledby="session-summary-heading">
                <h2 id="session-summary-heading">Review configuration</h2>
                <dl>
                    <div><dt>Session</dt><dd>{name.trim() || "Unnamed"} · {playType === "Versus" ? `Versus · ${visibility.replace("_", " ")}` : "Single player · private"}</dd></div>
                    <div><dt>Rounds</dt><dd>{rounds} × {questionCount} questions{playType === "Versus" ? ` · ${timeLimitMinutes} minutes each` : " · no timer"}</dd></div>
                    <div><dt>Commands</dt><dd>{selectedCommands.length ? selectedCommands.map(command => `${command.toUpperCase()} (${getState(command).options.length || "basic"}${getState(command).options.length ? " modes" : ""})`).join(", ") : "Choose at least one"}</dd></div>
                    <div><dt>Pipes</dt><dd>{allowPipes ? "Allowed" : "Off"}</dd></div>
                </dl>
                {selectedModes > questionCount && <p className="pool-note">You selected {selectedModes} modes for {questionCount} questions per round. Only some modes may appear in each round.</p>}
                {basicCommands.length > 0 && <p className="pool-note">Basic questions are available for {basicCommands.map(command => command.toUpperCase()).join(", ")}.</p>}
                {errors.submit && <p className="session-create-error" role="alert">{errors.submit}</p>}
                <button className="submit-btn" type="submit" disabled={submitting}>{submitting ? "Creating session…" : "Create session"}</button>
            </section>
        </form>
    </main>;
}

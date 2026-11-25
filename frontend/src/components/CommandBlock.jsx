import { useState } from "react";
import "./CommandBlock.css";

export default function CommandBlock({ command, description, groups, options, commandSelected, onCommandToggle, selectedOptions, onOptionToggle, onToggleAllOptions }) {
    const [expanded, setExpanded] = useState(false);
    const allSelected = options.every(option => selectedOptions.includes(option));

    return <section className={`command-block ${commandSelected ? "command-active" : ""}`} aria-label={`${command} command`}>
        <div className="command-header">
            <label className="command-choice">
                <input type="checkbox" checked={commandSelected} onChange={() => onCommandToggle(command)} />
                <span><strong>{command.toUpperCase()}</strong><small>{description}</small></span>
            </label>
            <button type="button" className="command-expand" aria-expanded={expanded} aria-controls={`${command}-modes`} onClick={() => setExpanded(value => !value)}>
                {commandSelected ? `${selectedOptions.length}/${options.length} modes` : "Off"} <span aria-hidden="true">{expanded ? "▾" : "▸"}</span>
            </button>
        </div>
        {expanded && <div id={`${command}-modes`} className="command-options-list">
            <p className="session-field-help">{commandSelected ? "Choose question modes for this command. No modes selected means basic questions only." : `Select ${command.toUpperCase()} to enable its modes.`}</p>
            <button type="button" className="command-options-toggle" disabled={!commandSelected} onClick={() => onToggleAllOptions(command, options)}>
                {allSelected ? `Clear ${command.toUpperCase()} modes` : `Select all ${command.toUpperCase()} modes`}
            </button>
            <div className="option-groups">{groups.map(group => <fieldset key={group.name} disabled={!commandSelected}>
                <legend>{group.name}</legend>
                {group.options.map(([name, help]) => <label key={name} className="option-row">
                    <input type="checkbox" checked={commandSelected && selectedOptions.includes(name)} onChange={() => onOptionToggle(command, name)} />
                    <span><strong>{name}</strong><small>{help}</small></span>
                </label>)}
            </fieldset>)}</div>
        </div>}
    </section>;
}

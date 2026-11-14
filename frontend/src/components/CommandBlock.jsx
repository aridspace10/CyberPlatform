import './CommandBlock.css'
import { useState } from 'react';

export default function CommandBlock({ command, options, commandSelected, onCommandToggle, selectedOptions, onOptionToggle, onToggleAllOptions }) {
    const [collapsed, setCollapsed] = useState(true);
    const allOptionsSelected = commandSelected && options.every(opt => selectedOptions.includes(opt));

    const handleCommandToggle = (e) => {
        e.stopPropagation();
        onCommandToggle(command, options);
    };

    return (
        <div className={`command-block ${!collapsed ? "expanded" : ""} ${commandSelected ? "command-active" : ""}`}>
            <div className="command-header" onClick={() => setCollapsed(p => !p)}>
                <div className="command-header-left">
                    <div
                        className={`command-checkbox ${commandSelected ? "checked" : ""}`}
                        onClick={handleCommandToggle}
                    >
                        {commandSelected && <span className="checkmark">✓</span>}
                    </div>
                    <span className="command-name">{command}</span>
                </div>
                <div className="command-header-right">
                    {commandSelected && (
                        <span className="command-count">{selectedOptions.length}/{options.length}</span>
                    )}
                    <span className={`chevron ${!collapsed ? "open" : ""}`}>▸</span>
                </div>
            </div>
            {!collapsed && (
                <div className="command-options-list">
                    <div className="command-options-actions">
                        <button
                            type="button"
                            className="command-options-toggle"
                            onClick={() => onToggleAllOptions(command, options)}
                        >
                            {allOptionsSelected ? "Clear options" : "Select all options"}
                        </button>
                    </div>
                    {options.map(opt => {
                        const optEnabled = commandSelected && selectedOptions.includes(opt);
                        return (
                            <label key={opt} className={`option-row ${!commandSelected ? "option-disabled" : ""}`}>
                                <input
                                    type="checkbox"
                                    checked={optEnabled}
                                    disabled={!commandSelected}
                                    onChange={() => commandSelected && onOptionToggle(command, opt)}
                                />
                                <span>{opt}</span>
                            </label>
                        );
                    })}
                </div>
            )}
        </div>
    );
}

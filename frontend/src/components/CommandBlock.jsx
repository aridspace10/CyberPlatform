import './CommandBlock.css'

export default function CommandBlock({ command, options }) {
    const [collapsed, setCollapsed] = useState(true);
    const [selected, setSelected] = useState([]);
 
    const toggleOption = (opt) => {
        setSelected(prev =>
            prev.includes(opt) ? prev.filter(o => o !== opt) : [...prev, opt]
        );
    };
 
    return (
        <div className={`command-block ${!collapsed ? "expanded" : ""}`}>
            <div className="command-header" onClick={() => setCollapsed(p => !p)}>
                <span className="command-name">{command}</span>
                <div className="command-header-right">
                    <span className="command-count">{selected.length}/{options.length}</span>
                    <span className={`chevron ${!collapsed ? "open" : ""}`}>▸</span>
                </div>
            </div>
            {!collapsed && (
                <div className="command-options-list">
                    {options.map(opt => (
                        <label key={opt} className="option-row">
                            <input
                                type="checkbox"
                                checked={selected.includes(opt)}
                                onChange={() => toggleOption(opt)}
                            />
                            <span>{opt}</span>
                        </label>
                    ))}
                </div>
            )}
        </div>
    );
}
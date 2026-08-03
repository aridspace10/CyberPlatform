import './NumberSelector.css';

export default function NumberSelector({ value, onChange, min = 1, max = 20, label }) {
    const decrement = () => { if (value > min) onChange(value - 1); };
    const increment = () => { if (value < max) onChange(value + 1); };

    const handleInput = (e) => {
        const parsed = parseInt(e.target.value, 10);
        if (!isNaN(parsed)) onChange(Math.min(max, Math.max(min, parsed)));
    };

    return (
        <div className="number-selector">
            {label && <span className="field-label">{label}</span>}
            <div className="number-selector-control">
                <button
                    className="num-btn"
                    onClick={decrement}
                    disabled={value <= min}
                >−</button>
                <input
                    type="number"
                    className="num-input"
                    value={value}
                    onChange={handleInput}
                    min={min}
                    max={max}
                />
                <button
                    className="num-btn"
                    onClick={increment}
                    disabled={value >= max}
                >+</button>
            </div>
        </div>
    );
}
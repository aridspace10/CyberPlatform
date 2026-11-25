import './NumberSelector.css';

export default function NumberSelector({ value, onChange, min = 1, max = 20, label, id, describedBy, invalid }) {
    const decrement = () => { if (value > min) onChange(value - 1); };
    const increment = () => { if (value < max) onChange(value + 1); };

    const handleInput = (e) => {
        const parsed = parseInt(e.target.value, 10);
        if (!isNaN(parsed)) onChange(Math.min(max, Math.max(min, parsed)));
    };

    return (
        <div className="number-selector">
            {label && <label className="field-label" htmlFor={id}>{label}</label>}
            <div className="number-selector-control">
                <button
                    type="button"
                    aria-label={`Decrease ${label}`}
                    className="num-btn"
                    onClick={decrement}
                    disabled={value <= min}
                >−</button>
                <input
                    id={id}
                    aria-label={label}
                    aria-describedby={describedBy}
                    aria-invalid={invalid || undefined}
                    type="number"
                    className="num-input"
                    value={value}
                    onChange={handleInput}
                    min={min}
                    max={max}
                />
                <button
                    type="button"
                    aria-label={`Increase ${label}`}
                    className="num-btn"
                    onClick={increment}
                    disabled={value >= max}
                >+</button>
            </div>
        </div>
    );
}

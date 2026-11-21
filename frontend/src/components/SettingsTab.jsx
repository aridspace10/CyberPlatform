import { DEFAULT_SANDBOX_SETTINGS } from "../game/sandboxSettings";
import "./SettingsTab.css";

export default function SettingsTab({ isSandbox, settings, onChange, onReset }) {
    if (!isSandbox) {
        return <div className="settings-tab"><h1>Settings</h1></div>;
    }

    return (
        <div className="settings-tab">
            <h1>Sandbox settings</h1>
            <p className="settings-intro">Your display preferences are saved on this device.</p>

            <label className="setting-row" htmlFor="terminal-font-size">
                <span className="setting-copy">
                    <strong>Terminal font size</strong>
                    <small>Change the command text size.</small>
                </span>
                <select id="terminal-font-size" value={settings.fontSize} onChange={event => onChange("fontSize", Number(event.target.value))}>
                    {[12, 14, 16, 18, 20].map(size => <option key={size} value={size}>{size} px</option>)}
                </select>
            </label>

            <label className="setting-row">
                <span className="setting-copy">
                    <strong>Wrap long lines</strong>
                    <small>Keep long output within the terminal.</small>
                </span>
                <input type="checkbox" checked={settings.wrapLines} onChange={event => onChange("wrapLines", event.target.checked)} />
            </label>

            <label className="setting-row">
                <span className="setting-copy">
                    <strong>High contrast</strong>
                    <small>Brighten text and borders.</small>
                </span>
                <input type="checkbox" checked={settings.highContrast} onChange={event => onChange("highContrast", event.target.checked)} />
            </label>

            <label className="setting-row">
                <span className="setting-copy">
                    <strong>Reduced motion</strong>
                    <small>Limit interface animations.</small>
                </span>
                <input type="checkbox" checked={settings.reducedMotion} onChange={event => onChange("reducedMotion", event.target.checked)} />
            </label>

            <label className="setting-row">
                <span className="setting-copy">
                    <strong>Chat notifications</strong>
                    <small>Show a badge for new messages.</small>
                </span>
                <input type="checkbox" checked={settings.chatNotifications} onChange={event => onChange("chatNotifications", event.target.checked)} />
            </label>

            <button className="settings-reset" type="button" onClick={onReset} disabled={Object.keys(DEFAULT_SANDBOX_SETTINGS).every(key => settings[key] === DEFAULT_SANDBOX_SETTINGS[key])}>
                Reset to defaults
            </button>
        </div>
    );
}

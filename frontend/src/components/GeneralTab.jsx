import { useSession } from "./SessionContext";
import { useNavigate } from "react-router";
import { useState } from "react";
import { downloadSessionDiagnostics } from "../api/sessions";
import { saveSessionRequest } from "../api/saveSession";
import { API_URL } from "../api/config";
import "./Tabs.css";
import { PUBLIC_SANDBOX_ONLY } from "../publicLaunch";

export default function GeneralTab({ isSandbox, onResetSandbox, resetPending, resetError }) {
    const { sessionId, addCommandLine } = useSession();
    const navigate = useNavigate();
    const [diagnosticsError, setDiagnosticsError] = useState("");
    const [saveError, setSaveError] = useState("");
    const [saving, setSaving] = useState(false);

    const handleSave = async () => {
        if (saving) return;
        setSaving(true);
        setSaveError("");
        try {
            await saveSessionRequest(fetch, `${API_URL}/sessions/${sessionId}/save`, localStorage.getItem("token"));
            addCommandLine("[SYSTEM] Game Saved");
        } catch (error) {
            setSaveError(error.message);
        } finally {
            setSaving(false);
        }
    }

    const handleDownloadDiagnostics = async () => {
        setDiagnosticsError("");
        try {
            await downloadSessionDiagnostics(sessionId);
        } catch (error) {
            setDiagnosticsError(error.message);
        }
    };

    const handleExit = () => {
        navigate("/")
    }

    const handleReportIssue = () => {
        navigate("/contact", { state: { page: window.location.pathname } });
    };

    return (
        <div className="general-tab">
            <h1>General</h1>
            <div className="save-action">
                <button className="tab-button" onClick={handleSave} disabled={saving}>
                    {saving ? "Saving..." : "Save"}
                </button>
                {saveError && <p role="alert">{saveError}</p>}
            </div>
            <div className="diagnostics-action">
                <button className="tab-button" onClick={handleDownloadDiagnostics}>
                    Download diagnostics
                </button>
                <small>Contains only your activity and errors from this session.</small>
                {diagnosticsError && <p role="alert">{diagnosticsError}</p>}
            </div>
            <button className="tab-button" onClick={handleReportIssue}>Report an issue</button>
            {isSandbox && !PUBLIC_SANDBOX_ONLY && <>
                <button className="tab-button" type="button" onClick={onResetSandbox} disabled={resetPending}>
                    {resetPending ? "Resetting…" : "Reset Sandbox"}
                </button>
                {resetError && <p role="alert">{resetError}</p>}
            </>}
            <button className="tab-button" onClick={handleExit}>Exit</button>
        </div>
    )
}

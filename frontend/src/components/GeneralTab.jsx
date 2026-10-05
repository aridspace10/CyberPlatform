import { useSession } from "./SessionContext";
import { useNavigate } from "react-router";
import { useState } from "react";
import { downloadSessionDiagnostics } from "../api/sessions";
import { API_URL } from "../api/config";
import "./Tabs.css";

export default function GeneralTab() {
    const { sessionId, addCommandLine } = useSession();
    const navigate = useNavigate();
    const [diagnosticsError, setDiagnosticsError] = useState("");

    const handleSave = async () => {
        await fetch(`${API_URL}/sessions/${sessionId}/save`, {
            method: "POST"
        })
        addCommandLine("[SYSTEM] Game Saved")
    }

    const handleReset = () => {

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

    return (
        <div>
            <div className="general-tab">
                <h1> General </h1>
                <button className="tab-button" onClick={handleSave}> Save </button>
                <button className="tab-button" onClick={handleDownloadDiagnostics}>
                    Download diagnostics
                </button>
                <small>Contains only your activity and errors from this session.</small>
                {diagnosticsError && <p role="alert">{diagnosticsError}</p>}
                <button className="tab-button" onClick={handleReset}> Reset </button>
                <button className="tab-button"onClick={handleExit}> Exit </button>
            </div>
        </div>
    )
}

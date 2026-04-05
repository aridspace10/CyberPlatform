import { useState } from "react";
import { useSession } from "./SessionContext";
import "./Tabs.css"

export default function GeneralTab() {
    const { sessionId } = useSession();
    const [saved, setSaved] = useState(false);

    const handleSave = async () => {
        await fetch(`http://localhost:8000/api/sessions/${sessionId}/save`, {
            method: "POST"
        })
    }

    const handleReset = () => {

    }

    const handleExit = () => {
        
    }

    return (
        <div>
            <div className="general-tab">
                <h1> General </h1>
                <button className="tab-button" onClick={handleSave}> Save </button>
                <button className="tab-button" onClick={handleReset}> Reset </button>
                <button className="tab-button"onClick={handleExit}> Exit </button>
            </div>
        </div>
    )
}
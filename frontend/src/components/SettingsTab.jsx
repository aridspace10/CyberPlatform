export default function SettingsTab() {

    const handleReset = () => {

    }

    const handleExit = () => {
        
    }

    return (
        <div className="settings-tab">
            <h1> Settings </h1>
            <button onClick={handleReset}> Reset </button>
            <button onClick={handleExit}> Exit </button>
        </div>
    )
}
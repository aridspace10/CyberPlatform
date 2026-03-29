export default function GeneralTab() {

    const handleReset = () => {

    }

    const handleExit = () => {
        
    }

    return (
        <div className="general-tab">
            <h1> General </h1>
            <button onClick={handleReset}> Reset </button>
            <button onClick={handleExit}> Exit </button>
        </div>
    )
}
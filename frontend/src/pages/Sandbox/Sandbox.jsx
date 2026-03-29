import SettingsTab from "../../components/SettingsTab"

export default function Sandbox() {
    let content = <GeneralTab />

    const handleTabSwitch = (tab) => {
        switch (tab) {
            case "General":
                content = <GeneralTab />
            case "Settings":
                content = <SettingsTab />
            case "Environment":
                content = <EnvironmentTab />
        }
    }

    return (
        <div className="sandbox-page">
            <div className="main-screen">

            </div>
            <div className="sidebar-page">
                <div className="sidebar-nav">
                    <button onClick={() => handleTabSwitch("General")}> General </button>
                    <button onClick={() => handleTabSwitch("Settings")}> Settings </button>
                    <button onClick={() => handleTabSwitch("Environment")}> Environment </button>
                </div>
                {content}
            </div>
        </div>
    )
}
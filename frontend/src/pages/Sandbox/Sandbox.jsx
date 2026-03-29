import SettingsTab from "../../components/SettingsTab"

export default function Sandbox() {
    let content = <SettingsTab></SettingsTab>
    return (
        <div className="sandbox-page">
            <div className="main-screen">

            </div>
            <div className="sidebar-page">
                <div className="sidebar-nav">

                </div>
                {content}
            </div>
        </div>
    )
}
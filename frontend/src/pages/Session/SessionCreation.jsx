import { useEffect, useRef, useState } from "react";
export default function SessionCreation() {
    const [name, setName] = useState("");
    const commands = ["grep"]

    return (
        <div className="session-create-page">
            <div className="create-left-side">
                <input
                    type="text"
                    placeholder="Name"
                    value={name}
                    onChange={e => setName(e.target.value)}
                    autoComplete="name"
                    spellCheck={false}
                />
            </div>
            <div className="create-right-side">
                <h1> Allowed Commands </h1>
                <div className="command-options">
                    <button> Select All </button>
                    <button> Deselect All </button>
                </div>
                <div className="commands">
                    {commands.map(command => 
                        <div className="command">
                            <h1> command </h1>
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
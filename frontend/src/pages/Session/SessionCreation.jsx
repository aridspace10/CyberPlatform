import { useEffect, useRef, useState } from "react";
export default function SessionCreation() {
    const [name, setName] = useState("");
    return (
        <div className="session-create-page">
            <input
                type="text"
                placeholder="Name"
                value={name}
                onChange={e => setname(e.target.value)}
                onKeyDown={handleKeyDown}
                autoComplete="name"
                spellCheck={false}
            />
        </div>
    )
}
import { createContext, useContext, useState } from "react";

export const SessionContext = createContext(null);

export function SessionProvider({ sessionId, wsRef, children }) {
    const [vimMode, setVimMode] = useState(false);
    const [vimData, setVimData] = useState([]);

    const openVim = (data) => {
        setVimData(data);
        setVimMode(true);
    };
    const closeVim = () => setVimMode(false);

    return (
        <SessionContext.Provider value={{ sessionId, wsRef, vimMode, vimData, openVim, closeVim }}>
            {children}
        </SessionContext.Provider>
    );
}

export const useSession = () => useContext(SessionContext);
import { API_URL } from "./config";

const API = API_URL;

export async function enterTutorial(user_id) {
    const res = await fetch(`${API}/sandbox/${user_id}`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
        body: JSON.stringify({ user_id })
    });

    const data = await res.json();
    return data
}

export async function getFullSessionData(session_id) {
    const res = await fetch(`${API}/session/${session_id}`, {
        method: "GET",
        headers: { Authorization: `Bearer ${localStorage.getItem("token")}` },
    });

    const data = await res.json();
    if (!res.ok) {
        throw new Error(data.detail || "Could not load the session");
    }
    return data
}

export async function createSession(config) {
    const res = await fetch(`${API}/session_create`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
        body: JSON.stringify({ config })
    });

    const data = await res.json();
    if (!res.ok) {
        const detail = data.detail;
        const message = typeof detail === "string"
            ? detail
            : Array.isArray(detail)
                ? detail.map(error => error.msg || "Invalid session configuration").join("; ")
                : "Could not create the session";
        throw new Error(message);
    }
    return data;
}

async function sessionAction(path, method = "GET") {
    const response = await fetch(`${API}${path}`, {
        method,
        headers: { Authorization: `Bearer ${localStorage.getItem("token")}` },
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Session request failed");
    return data;
}

export const getSessionAccess = sessionId => sessionAction(`/session/${sessionId}/access`);
export const requestSessionJoin = sessionId => sessionAction(`/session/${sessionId}/requests`, "POST");
export const getSessionRequests = sessionId => sessionAction(`/session/${sessionId}/requests`);
export const answerSessionRequest = (sessionId, userId, decision) =>
    sessionAction(`/session/${sessionId}/requests/${userId}/${decision}`, "POST");

export async function downloadSessionDiagnostics(sessionId) {
    const token = localStorage.getItem("token");
    const res = await fetch(`${API}/session/${sessionId}/diagnostics`, {
        headers: { Authorization: `Bearer ${token}` }
    });

    if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Could not download session diagnostics");
    }

    const downloadUrl = URL.createObjectURL(await res.blob());
    const link = document.createElement("a");
    link.href = downloadUrl;
    link.download = `session-${sessionId}-diagnostics.zip`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(downloadUrl), 1000);
}

const API = "http://localhost:8000/api";

export async function enterTutorial(user_id) {
    const res = await fetch(`${API}/sandbox/${user_id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id })
    });

    const data = await res.json();
    return data
}

export async function getFullSessionData(session_id) {
    const res = await fetch(`${API}/session/${session_id}`, {
        method: "GET",
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
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ config })
    });

    const data = await res.json();
    if (!res.ok) {
        throw new Error(data.detail || "Could not create the session");
    }
    return data;
}

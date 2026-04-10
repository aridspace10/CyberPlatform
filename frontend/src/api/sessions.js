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

export async function getFullSessionData(session_id, user_id) {
    const res = await fetch(`${API}/session/${session_id}`, {
        method: "GET",
    });

    const data = await res.json();
    return data
}

export async function getUserCommand(session_id, user_id, count) {
    const res = await fetch(`${API}/session/${session_id}/user/${user_id}/command/${count}`, {
        method: "GET"
    });

    const data = await res.json();
    return data;
}
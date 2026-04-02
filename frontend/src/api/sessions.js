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
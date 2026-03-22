const API = "http://localhost:8000/sessions";

export async function enterTutorial(user_id) {
    const res = await fetch(`${API}/sandbox/${user}`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(user_id)
    });

    const data = await res.json();
    console.log(data)
}
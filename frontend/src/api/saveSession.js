export async function saveSessionRequest(fetcher, url, token) {
    let response;
    try {
        response = await fetcher(url, {
            method: "POST",
            headers: { Authorization: `Bearer ${token}` },
        });
    } catch {
        throw new Error("Could not reach the server. Please try saving again.");
    }

    if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        const detail = typeof data.detail === "string" ? data.detail : null;
        throw new Error(detail || "Could not save the game. Please try again.");
    }
}

import assert from "node:assert/strict";
import test from "node:test";
import { saveSessionRequest } from "../src/api/saveSession.js";

const url = "http://localhost:8000/api/sessions/7/save";

test("a successful save sends authorization and resolves", async () => {
    let request;
    await saveSessionRequest(async (...args) => {
        request = args;
        return { ok: true };
    }, url, "valid-token");
    assert.deepEqual(request, [url, {
        method: "POST",
        headers: { Authorization: "Bearer valid-token" },
    }]);
});

for (const status of [403, 500]) {
    test(`a ${status} response rejects with the API error`, async () => {
        await assert.rejects(
            saveSessionRequest(async () => ({
                ok: false,
                json: async () => ({ detail: "Save rejected" }),
            }), url, "valid-token"),
            /Save rejected/,
        );
    });
}

test("a network failure rejects with a retryable message", async () => {
    await assert.rejects(
        saveSessionRequest(async () => { throw new TypeError("Failed to fetch"); }, url, "valid-token"),
        /Could not reach the server/,
    );
});

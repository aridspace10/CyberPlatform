import assert from "node:assert/strict";
import { after, before, test } from "node:test";
import { JSDOM } from "jsdom";
import React, { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter } from "react-router";
import { createServer } from "vite";

const dom = new JSDOM("<!doctype html><html><body></body></html>", { url: "http://localhost/" });
globalThis.window = dom.window;
globalThis.document = dom.window.document;
globalThis.localStorage = dom.window.localStorage;
globalThis.MouseEvent = dom.window.MouseEvent;
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

let vite;
let GeneralTab;
let SessionContext;

before(async () => {
    vite = await createServer({ server: { middlewareMode: true }, appType: "custom" });
    ({ default: GeneralTab } = await vite.ssrLoadModule("/src/components/GeneralTab.jsx"));
    ({ SessionContext } = await vite.ssrLoadModule("/src/components/SessionContext.js"));
});

after(async () => {
    await vite?.close();
    dom.window.close();
});

async function renderSaveButton(fetcher) {
    const container = document.createElement("div");
    document.body.appendChild(container);
    const root = createRoot(container);
    const lines = [];
    globalThis.fetch = fetcher;
    localStorage.setItem("token", "valid-token");

    await act(async () => {
        root.render(createElement(MemoryRouter, null,
            createElement(SessionContext.Provider, {
                value: { sessionId: "7", addCommandLine: line => lines.push(line) },
            }, createElement(GeneralTab))));
    });

    return {
        container,
        lines,
        button: () => [...container.querySelectorAll("button")].find(button => button.textContent === "Save" || button.textContent === "Saving..."),
        click: async () => act(async () => {
            const button = [...container.querySelectorAll("button")].find(button => button.textContent === "Save" || button.textContent === "Saving...");
            button.dispatchEvent(new MouseEvent("click", { bubbles: true }));
        }),
        unmount: async () => {
            await act(async () => root.unmount());
            container.remove();
        },
    };
}

test("Save reports success only after the server accepts it", async () => {
    let request;
    const ui = await renderSaveButton(async (...args) => {
        request = args;
        return { ok: true };
    });
    try {
        await ui.click();
        assert.deepEqual(request, ["http://localhost:8000/api/sessions/7/save", {
            method: "POST",
            headers: { Authorization: "Bearer valid-token" },
        }]);
        assert.deepEqual(ui.lines, ["[SYSTEM] Game Saved"]);
        assert.equal(ui.container.querySelector("[role=alert]"), null);
    } finally {
        await ui.unmount();
    }
});

for (const status of [403, 500]) {
    test(`Save shows a ${status} failure beside the button`, async () => {
        const ui = await renderSaveButton(async () => ({
            ok: false,
            status,
            json: async () => ({ detail: "Save rejected" }),
        }));
        try {
            await ui.click();
            assert.deepEqual(ui.lines, []);
            assert.match(ui.container.querySelector(".save-action [role=alert]").textContent, /Save rejected/);
        } finally {
            await ui.unmount();
        }
    });
}

test("Save shows a network failure beside the button", async () => {
    const ui = await renderSaveButton(async () => { throw new TypeError("Failed to fetch"); });
    try {
        await ui.click();
        assert.deepEqual(ui.lines, []);
        assert.match(ui.container.querySelector(".save-action [role=alert]").textContent, /Could not reach the server/);
    } finally {
        await ui.unmount();
    }
});

test("Save disables repeat clicks while the request is pending", async () => {
    let resolveRequest;
    let requests = 0;
    const ui = await renderSaveButton(() => {
        requests += 1;
        return new Promise(resolve => { resolveRequest = resolve; });
    });
    try {
        await ui.click();
        assert.equal(ui.button().disabled, true);
        await ui.click();
        assert.equal(requests, 1);
        await act(async () => resolveRequest({ ok: true }));
        assert.equal(ui.button().disabled, false);
    } finally {
        await ui.unmount();
    }
});

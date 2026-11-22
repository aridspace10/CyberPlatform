import assert from "node:assert/strict";
import { after, before, test } from "node:test";
import { JSDOM } from "jsdom";
import React, { act, createElement } from "react";
import { MemoryRouter, Route, Routes } from "react-router";
import { createServer } from "vite";

const dom = new JSDOM("<!doctype html><html><body></body></html>", { url: "http://localhost/" });
globalThis.window = dom.window;
globalThis.document = dom.window.document;
globalThis.localStorage = dom.window.localStorage;
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const sockets = [];
class FakeWebSocket {
    static OPEN = 1;
    static CLOSED = 3;
    constructor(url) {
        this.url = url;
        this.readyState = 0;
        this.sent = [];
        sockets.push(this);
    }
    open() {
        this.readyState = FakeWebSocket.OPEN;
        this.onopen?.();
    }
    send(value) { this.sent.push(JSON.parse(value)); }
    receive(message) { this.onmessage?.({ data: JSON.stringify(message) }); }
    close(code = 1000) {
        if (this.readyState === FakeWebSocket.CLOSED) return;
        this.readyState = FakeWebSocket.CLOSED;
        this.onclose?.({ code });
    }
}
globalThis.WebSocket = FakeWebSocket;

let vite;
let Game;
let AuthContext;
let createRoot;

before(async () => {
    ({ createRoot } = await import("react-dom/client"));
    vite = await createServer({ server: { middlewareMode: true, hmr: false }, appType: "custom" });
    ({ default: Game } = await vite.ssrLoadModule("/src/game/Game.jsx"));
    ({ AuthContext } = await vite.ssrLoadModule("/src/auth/auth-context.js"));
});

after(async () => {
    await vite?.close();
    dom.window.close();
});

async function renderGame() {
    sockets.length = 0;
    localStorage.setItem("token", "first-token");
    const container = document.createElement("div");
    document.body.appendChild(container);
    const root = createRoot(container);
    let logouts = 0;
    await act(async () => {
        root.render(createElement(AuthContext.Provider, {
            value: { user: { id: 1, username: "alice" }, logout: () => { logouts += 1; } },
        }, createElement(MemoryRouter, { initialEntries: ["/game/7"] },
            createElement(Routes, null, createElement(Route, { path: "/game/:sessionId", element: createElement(Game) })))));
    });
    return {
        container,
        get logouts() { return logouts; },
        socket: () => sockets.at(-1),
        unmount: async () => {
            await act(async () => root.unmount());
            container.remove();
            localStorage.clear();
        },
    };
}

test("unexpected closure clears stale state and reconnects with the current token", async () => {
    const ui = await renderGame();
    try {
        const first = ui.socket();
        assert.match(first.url, /\/ws\/7$/);
        await act(async () => first.open());
        assert.deepEqual(first.sent, [{ type: "join", token: "first-token" }]);
        await act(async () => first.receive({ type: "lobby_update", players: ["alice"], state: "running" }));
        assert.ok(ui.container.querySelector("input[aria-label='Terminal command']"));

        await act(async () => first.close(1006));
        assert.match(ui.container.querySelector(".session-connection-panel").textContent, /Connection lost/);
        assert.equal(ui.container.querySelector("input[aria-label='Terminal command']"), null);
        assert.doesNotMatch(ui.container.textContent, /Loading\.\.\./);

        localStorage.setItem("token", "refreshed-token");
        await act(async () => ui.container.querySelector(".session-connection-panel button").dispatchEvent(
            new window.MouseEvent("click", { bubbles: true })));
        const second = ui.socket();
        assert.notEqual(second, first);
        await act(async () => second.open());
        assert.deepEqual(second.sent, [{ type: "join", token: "refreshed-token" }]);
        await act(async () => second.receive({ type: "lobby_update", players: ["alice"], state: "finished" }));
        assert.match(ui.container.textContent, /Game complete/);
        assert.equal(ui.container.querySelector(".session-connection-panel"), null);
    } finally {
        await ui.unmount();
    }
});

test("initial failure offers retry instead of leaving Loading on screen", async () => {
    const ui = await renderGame();
    try {
        await act(async () => ui.socket().close(1006));
        assert.ok(ui.container.querySelector(".session-connection-panel button"));
        assert.doesNotMatch(ui.container.textContent, /Loading\.\.\./);
    } finally {
        await ui.unmount();
    }
});

test("intentional missing-session and auth closures do not offer reconnect", async () => {
    const missing = await renderGame();
    try {
        await act(async () => missing.socket().close(4404));
        assert.match(missing.container.textContent, /Session not found/);
        assert.equal(missing.container.querySelector(".session-connection-panel"), null);
    } finally {
        await missing.unmount();
    }

    const auth = await renderGame();
    try {
        await act(async () => auth.socket().close(4401));
        assert.equal(auth.logouts, 1);
        assert.equal(auth.container.querySelector(".session-connection-panel"), null);
    } finally {
        await auth.unmount();
    }
});

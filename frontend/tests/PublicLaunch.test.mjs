import assert from "node:assert/strict";
import { after, before, test } from "node:test";
import { JSDOM } from "jsdom";
import React, { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter, Route, Routes } from "react-router";
import { createServer } from "vite";

const dom = new JSDOM("<!doctype html><html><body></body></html>", { url: "http://localhost/" });
globalThis.window = dom.window;
globalThis.document = dom.window.document;
globalThis.localStorage = dom.window.localStorage;
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
// React's legacy input event path expects these methods in the test DOM.
dom.window.HTMLElement.prototype.attachEvent = () => {};
dom.window.HTMLElement.prototype.detachEvent = () => {};

let vite;
let App;
let Game;
let AuthContext;
let socket;

class FakeWebSocket {
    static OPEN = 1;
    static CLOSED = 3;
    readyState = 0;
    constructor() { socket = this; }
    send() {}
    close() { this.readyState = FakeWebSocket.CLOSED; }
}
globalThis.WebSocket = FakeWebSocket;

before(async () => {
    process.env.VITE_PUBLIC_SANDBOX_ONLY = "true";
    vite = await createServer({ mode: "production", server: { middlewareMode: true }, appType: "custom" });
    ({ default: App } = await vite.ssrLoadModule("/src/App.jsx"));
    ({ default: Game } = await vite.ssrLoadModule("/src/game/Game.jsx"));
    ({ AuthContext } = await vite.ssrLoadModule("/src/auth/auth-context.js"));
});

after(async () => {
    await vite?.close();
    delete process.env.VITE_PUBLIC_SANDBOX_ONLY;
    dom.window.close();
});

test("public build hides session navigation and redirects session routes", async () => {
    for (const path of ["/sessions", "/session-create"]) {
        window.history.pushState({}, "", path);
        const container = document.createElement("div");
        document.body.appendChild(container);
        const root = createRoot(container);
        try {
            await act(async () => root.render(createElement(App)));
            assert.equal(window.location.pathname, "/");
            assert.match(container.textContent, /Learn the terminal/);
            assert.equal(container.querySelector('a[href="/sessions"]'), null);
        } finally {
            await act(async () => root.unmount());
            container.remove();
        }
    }
});

test("public Sandbox shows only General, Save, and diagnostics controls", async () => {
    const container = document.createElement("div");
    document.body.appendChild(container);
    const root = createRoot(container);
    try {
        await act(async () => root.render(createElement(AuthContext.Provider, {
            value: { user: { id: 42, username: "creator" }, logout: () => {} },
        }, createElement(MemoryRouter, { initialEntries: ["/game/7"] },
            createElement(Routes, null,
                createElement(Route, { path: "/game/:sessionId", element: createElement(Game) }))))));
        await act(async () => socket.onmessage({ data: JSON.stringify({
            type: "lobby_update", players: ["creator"], state: "running",
            gameData: { isSandbox: true, gameType: "Tutorial", creatorID: 42 },
        }) }));
        const controls = container.querySelector(".sidebar-nav").textContent;
        assert.match(controls, /General/);
        assert.doesNotMatch(controls, /Settings|Environment|Chat/);
        assert.equal(container.querySelector(".general-tab").textContent.includes("Reset Sandbox"), false);
        assert.match(container.querySelector(".general-tab").textContent, /Save/);
        assert.match(container.querySelector(".general-tab").textContent, /Download diagnostics/);
        assert.equal(container.querySelector('a[href="/sessions"]'), null);
    } finally {
        await act(async () => root.unmount());
        container.remove();
    }
});

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
    constructor() { this.readyState = 0; this.sent = []; sockets.push(this); }
    open() { this.readyState = 1; this.onopen?.(); }
    send(value) { this.sent.push(JSON.parse(value)); }
    receive(message) { this.onmessage?.({ data: JSON.stringify(message) }); }
    close(code = 1000) {
        if (this.readyState === 3) return;
        this.readyState = 3;
        this.onclose?.({ code });
    }
}
globalThis.WebSocket = FakeWebSocket;

let vite;
let Gamescreen;
let Game;
let AuthContext;
let createRoot;

before(async () => {
    ({ createRoot } = await import("react-dom/client"));
    vite = await createServer({ server: { middlewareMode: true, hmr: false }, appType: "custom" });
    ({ default: Gamescreen } = await vite.ssrLoadModule("/src/game/Gamescreen.jsx"));
    ({ default: Game } = await vite.ssrLoadModule("/src/game/Game.jsx"));
    ({ AuthContext } = await vite.ssrLoadModule("/src/auth/auth-context.js"));
});

after(async () => {
    await vite?.close();
    dom.window.close();
});

async function renderTerminal() {
    const container = document.createElement("div");
    document.body.appendChild(container);
    const root = createRoot(container);
    const sent = [];
    const lines = [];
    const wsRef = { current: { readyState: 1, send: value => sent.push(JSON.parse(value)) } };
    const render = async interaction => act(async () => {
        root.render(createElement(Gamescreen, {
            wsRef, commandLog: lines, addCommandLine: line => lines.push(line),
            username: "player", cwd: "/root", interaction,
        }));
    });
    const enter = async value => act(async () => {
        const input = container.querySelector("input.prompt");
        const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
        setter.call(input, value);
        input.dispatchEvent(new window.Event("input", { bubbles: true }));
        input.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    });
    await render(null);
    return { container, sent, lines, render, enter, unmount: async () => {
        await act(async () => root.unmount());
        container.remove();
    } };
}

test("confirmation and heredoc responses use the foreground prompt and skip command history", async () => {
    const ui = await renderTerminal();
    try {
        await ui.enter("rm -i alpha.txt");
        assert.deepEqual(ui.sent[0], { type: "command", input: "rm -i alpha.txt" });
        await ui.render({ mode: "foreground", prompt: "rm: remove regular file 'alpha.txt'?" });
        assert.match(ui.container.querySelector(".prompt-label").textContent, /remove regular file/);
        assert.equal(ui.container.querySelector("input.prompt").getAttribute("aria-label"), "Terminal response");
        assert.equal(ui.container.querySelector(".history-controls"), null);
        await ui.enter("y");
        assert.deepEqual(ui.sent[1], { type: "command", input: "y" });
        assert.match(ui.lines.at(-1), /^rm: remove regular file 'alpha\.txt'\? y$/);

        await ui.render({ mode: "foreground", prompt: ">" });
        await ui.enter("");
        assert.deepEqual(ui.sent[2], { type: "command", input: "" });
        await ui.render(null);
        assert.match(ui.container.querySelector(".prompt-label").textContent, /player@cyber:~\$/);
        assert.equal(ui.container.querySelector(".history-controls button").disabled, false);
    } finally {
        await ui.unmount();
    }
});

test("busy foreground tasks block input and expose cancellation", async () => {
    const ui = await renderTerminal();
    try {
        await ui.render({ mode: "foreground", prompt: "" });
        assert.equal(ui.container.querySelector("input.prompt").disabled, true);
        assert.match(ui.container.querySelector(".prompt-label").textContent, /Running/);
        await act(async () => ui.container.querySelector(".cancel-foreground").dispatchEvent(
            new window.MouseEvent("click", { bubbles: true })));
        assert.deepEqual(ui.sent, [{ type: "command", input: "^C" }]);
        await ui.render(null);
        assert.equal(ui.container.querySelector("input.prompt").disabled, false);
    } finally {
        await ui.unmount();
    }
});

test("game socket messages switch prompts and restore the command state", async () => {
    sockets.length = 0;
    localStorage.setItem("token", "test-token");
    const container = document.createElement("div");
    document.body.appendChild(container);
    const root = createRoot(container);
    try {
        await act(async () => root.render(createElement(AuthContext.Provider, {
            value: { user: { id: 1, username: "player" }, logout: () => {} },
        }, createElement(MemoryRouter, { initialEntries: ["/game/7"] },
            createElement(Routes, null, createElement(Route, {
                path: "/game/:sessionId", element: createElement(Game),
            }))))));
        const socket = sockets[0];
        await act(async () => socket.open());
        await act(async () => socket.receive({ type: "lobby_update", players: ["player"], state: "running" }));
        assert.match(container.querySelector(".prompt-label").textContent, /player@cyber/);

        await act(async () => socket.receive({
            type: "command_output", stdout: [], stderr: [], status: 0,
            interaction: { mode: "foreground", prompt: "rm: remove regular file 'alpha.txt'?" },
        }));
        assert.match(container.querySelector(".prompt-label").textContent, /remove regular file/);
        await act(async () => socket.receive({
            type: "command_output", stdout: [], stderr: [], status: 0,
            interaction: { mode: "foreground", prompt: ">" },
        }));
        assert.equal(container.querySelector(".prompt-label").textContent, ">");

        await act(async () => socket.receive({ type: "terminal_state", busy: false, mode: null, prompt: null }));
        assert.match(container.querySelector(".prompt-label").textContent, /player@cyber/);
        await act(async () => socket.receive({
            type: "command_output", stdout: [], stderr: [], status: 0,
            interaction: { mode: "foreground", prompt: "" },
        }));
        assert.equal(container.querySelector("input.prompt").disabled, true);
    } finally {
        await act(async () => root.unmount());
        container.remove();
        localStorage.clear();
    }
});

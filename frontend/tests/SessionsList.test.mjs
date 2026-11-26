import assert from "node:assert/strict";
import { after, before, test } from "node:test";
import { JSDOM } from "jsdom";
import React, { act, createElement } from "react";
import { MemoryRouter } from "react-router";
import { createServer } from "vite";

const dom = new JSDOM("<!doctype html><html><body></body></html>", { url: "http://localhost/" });
globalThis.window = dom.window;
globalThis.document = dom.window.document;
globalThis.localStorage = dom.window.localStorage;
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

let vite;
let SessionsList;
let createRoot;

before(async () => {
    ({ createRoot } = await import("react-dom/client"));
    vite = await createServer({ server: { middlewareMode: true, hmr: false }, appType: "custom" });
    ({ default: SessionsList } = await vite.ssrLoadModule("/src/components/SessionsList.jsx"));
});

after(async () => {
    await vite?.close();
    dom.window.close();
});

async function renderList(fetcher) {
    const container = document.createElement("div");
    document.body.appendChild(container);
    const root = createRoot(container);
    const originalInterval = window.setInterval;
    const originalClear = window.clearInterval;
    let tick;
    let interval;
    let cleared = false;
    window.setInterval = (callback, delay) => { tick = callback; interval = delay; return 77; };
    window.clearInterval = id => { if (id === 77) cleared = true; };
    Object.defineProperty(document, "hidden", { configurable: true, value: false });
    globalThis.fetch = fetcher;
    localStorage.setItem("token", "token");
    await act(async () => root.render(createElement(MemoryRouter, null,
        createElement(SessionsList, { user: { id: 7 }, authLoading: false }))));
    return {
        container, interval,
        tick: async () => act(async () => tick()),
        setHidden: value => Object.defineProperty(document, "hidden", { configurable: true, value }),
        visible: async () => act(async () => document.dispatchEvent(new window.Event("visibilitychange"))),
        unmount: async () => {
            await act(async () => root.unmount());
            container.remove();
            window.setInterval = originalInterval;
            window.clearInterval = originalClear;
            assert.equal(cleared, true);
        },
    };
}

const session = (id, name) => ({ id, name, play_type: "Versus", visibility: "public", state: "waiting", connected_players: 1, member: false });

test("refreshes every 10 seconds while visible and when returning to the page", async () => {
    let calls = 0;
    const ui = await renderList(async () => {
        calls += 1;
        return { ok: true, json: async () => ({ sessions: [session(calls, `Lobby ${calls}`)] }) };
    });
    try {
        assert.equal(ui.interval, 10_000);
        assert.match(ui.container.textContent, /Lobby 1/);
        await ui.tick();
        assert.match(ui.container.textContent, /Lobby 2/);
        ui.setHidden(true);
        await ui.tick();
        assert.equal(calls, 2);
        ui.setHidden(false);
        await ui.visible();
        assert.match(ui.container.textContent, /Lobby 3/);
    } finally { await ui.unmount(); }
});

test("failed background refresh keeps the current list and offers retry", async () => {
    let calls = 0;
    const ui = await renderList(async () => {
        calls += 1;
        if (calls === 2) return { ok: false, json: async () => ({ detail: "Temporary failure" }) };
        return { ok: true, json: async () => ({ sessions: [session(calls, `Lobby ${calls}`)] }) };
    });
    try {
        await ui.tick();
        assert.match(ui.container.querySelector("[role=alert]").textContent, /Could not load sessions/);
        assert.match(ui.container.textContent, /Lobby 1/);
        await act(async () => ui.container.querySelector(".sessions-error button").click());
        assert.match(ui.container.textContent, /Lobby 3/);
        assert.equal(ui.container.querySelector("[role=alert]"), null);
    } finally { await ui.unmount(); }
});

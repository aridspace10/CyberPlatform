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
globalThis.MouseEvent = dom.window.MouseEvent;
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
window.HTMLElement.prototype.attachEvent = () => {};
window.HTMLElement.prototype.detachEvent = () => {};

let vite;
let SessionCreation;
let AuthContext;
let createRoot;

before(async () => {
    ({ createRoot } = await import("react-dom/client"));
    vite = await createServer({ server: { middlewareMode: true, hmr: false }, appType: "custom" });
    ({ default: SessionCreation } = await vite.ssrLoadModule("/src/pages/Session/SessionCreation.jsx"));
    ({ AuthContext } = await vite.ssrLoadModule("/src/auth/auth-context.js"));
});

after(async () => {
    await vite?.close();
    dom.window.close();
});

async function renderForm(fetcher = async () => ({ ok: true, json: async () => ({ session_id: 42 }) })) {
    const container = document.createElement("div");
    document.body.appendChild(container);
    const root = createRoot(container);
    globalThis.fetch = fetcher;
    localStorage.setItem("token", "token");
    await act(async () => root.render(createElement(AuthContext.Provider, { value: { user: { id: 7 }, logout() {} } },
        createElement(MemoryRouter, { initialEntries: ["/create"] },
            createElement(Routes, null,
                createElement(Route, { path: "/create", element: createElement(SessionCreation) }),
                createElement(Route, { path: "/game/:id", element: createElement("p", null, "Game opened") }),
            )))));
    const click = async element => act(async () => element.dispatchEvent(new MouseEvent("click", { bubbles: true })));
    const button = text => {
        const found = [...container.querySelectorAll("button")].find(element => element.textContent.includes(text));
        assert.ok(found, `Missing button: ${text}`);
        return found;
    };
    const setInput = async (selector, value) => act(async () => {
        const input = container.querySelector(selector);
        input.focus();
        const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
        setter.call(input, value);
        input.dispatchEvent(new window.Event("input", { bubbles: true }));
        input.dispatchEvent(new window.Event("change", { bubbles: true }));
    });
    return { container, click, button, setInput, unmount: async () => { await act(async () => root.unmount()); container.remove(); } };
}

test("command selection, per-command modes, and pool summary stay in sync", async () => {
    const ui = await renderForm();
    try {
        const grep = ui.container.querySelector('[aria-label="grep command"]');
        const sed = ui.container.querySelector('[aria-label="sed command"]');
        assert.match(ui.container.textContent, /1\/6 commands selected/);
        await ui.click(grep.querySelector('input[type="checkbox"]'));
        await ui.click(sed.querySelector('input[type="checkbox"]'));
        assert.equal(grep.querySelector('input[type="checkbox"]').checked, false);
        assert.equal(sed.querySelector('input[type="checkbox"]').checked, true);
        await ui.click(sed.querySelector(".command-expand"));
        await ui.click(ui.button("Select all SED modes"));
        assert.match(ui.container.textContent, /19 selected modes/);
        assert.match(ui.container.textContent, /Only some modes may appear in each round/);
        await ui.click(ui.button("Clear SED modes"));
        assert.match(ui.container.textContent, /0 selected modes/);
        await ui.click(ui.button("Select all commands"));
        assert.match(ui.container.textContent, /6\/6 commands selected/);
        await ui.click(ui.button("Clear all commands"));
        assert.match(ui.container.textContent, /0\/6 commands selected/);
    } finally { await ui.unmount(); }
});

test("touch modification-time mode is sent in session creation", async () => {
    let payload;
    const ui = await renderForm(async (_url, options) => {
        payload = JSON.parse(options.body);
        return { ok: true, json: async () => ({ session_id: 42 }) };
    });
    try {
        const touch = ui.container.querySelector('[aria-label="touch command"]');
        const grep = ui.container.querySelector('[aria-label="grep command"]');
        await ui.click(grep.querySelector('input[type="checkbox"]'));
        await ui.click(touch.querySelector('input[type="checkbox"]'));
        await ui.click(touch.querySelector(".command-expand"));
        await ui.click(touch.querySelector(".option-row input"));
        await ui.setInput("#session-name", "File practice");
        await ui.click(ui.button("Create session"));
        assert.deepEqual(payload.config.commands.touch, { selected: true, options: ["Update Modified Time"] });
        assert.match(ui.container.textContent, /Game opened/);
    } finally { await ui.unmount(); }
});

test("validation appears beside name and command controls", async () => {
    const ui = await renderForm();
    try {
        await ui.click(ui.button("Create session"));
        assert.match(ui.container.querySelector("#session-name-error").textContent, /Enter a session name/);
        assert.equal(document.activeElement.id, "session-name");
        await ui.setInput("#session-name", "A round");
        await ui.click(ui.button("Clear all commands"));
        await ui.click(ui.button("Create session"));
        assert.match(ui.container.querySelector(".session-commands [role=alert]").textContent, /Select at least one command/);
    } finally { await ui.unmount(); }
});

test("rejected request preserves choices and shows server feedback", async () => {
    let payload;
    const ui = await renderForm(async (_url, options) => {
        payload = JSON.parse(options.body);
        return { ok: false, json: async () => ({ detail: "Session could not be saved" }) };
    });
    try {
        await ui.setInput("#session-name", "Practice");
        await ui.click(ui.container.querySelector('[aria-label="sed command"] input[type="checkbox"]'));
        await ui.click(ui.button("Create session"));
        assert.deepEqual(Object.keys(payload.config.commands).sort(), ["grep", "sed"]);
        assert.equal(payload.config.commands.sed.selected, true);
        assert.equal(ui.container.querySelector("#session-name").value, "Practice");
        assert.equal(ui.container.querySelector('[aria-label="sed command"] input[type="checkbox"]').checked, true);
        assert.match(ui.container.querySelector(".session-summary [role=alert]").textContent, /could not be saved/);
    } finally { await ui.unmount(); }
});

test("single player hides Versus controls and submits private visibility", async () => {
    let payload;
    const ui = await renderForm(async (_url, options) => {
        payload = JSON.parse(options.body);
        return { ok: true, json: async () => ({ session_id: 42 }) };
    });
    try {
        await ui.setInput("#session-name", "Solo");
        await act(async () => {
            const select = ui.container.querySelector("#session-play-type");
            select.value = "SinglePlayer";
            select.dispatchEvent(new window.Event("change", { bubbles: true }));
        });
        assert.equal(ui.container.querySelector("#session-visibility"), null);
        assert.equal(ui.container.querySelector("#session-time"), null);
        await ui.click(ui.button("Create session"));
        assert.equal(payload.config.visibility, "private");
        assert.match(ui.container.textContent, /Game opened/);
    } finally { await ui.unmount(); }
});

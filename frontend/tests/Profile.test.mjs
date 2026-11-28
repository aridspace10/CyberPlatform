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
let AuthContext;
let ProtectedRoute;
let Profile;
let createRoot;

before(async () => {
  ({ createRoot } = await import("react-dom/client"));
  vite = await createServer({ server: { middlewareMode: true }, appType: "custom" });
  ({ AuthContext } = await vite.ssrLoadModule("/src/auth/auth-context.js"));
  ({ default: ProtectedRoute } = await vite.ssrLoadModule("/src/auth/ProtectedRoute.jsx"));
  ({ default: Profile } = await vite.ssrLoadModule("/src/pages/Profile/Profile.jsx"));
});

after(async () => {
  await vite?.close();
  dom.window.close();
});

async function renderProfile(user, fetcher) {
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  globalThis.fetch = fetcher;
  localStorage.setItem("token", "test-token");
  await act(async () => {
    root.render(createElement(AuthContext.Provider, {
      value: { user, loading: false, logout: () => {} },
    }, createElement(MemoryRouter, { initialEntries: ["/profile"] },
      createElement(Routes, null,
        createElement(Route, { path: "/profile", element: createElement(ProtectedRoute, null, createElement(Profile)) }),
        createElement(Route, { path: "/login", element: createElement("p", null, "Sign in route") }),
      ),
    )));
  });
  return {
    container,
    click: async label => act(async () => {
      const button = [...container.querySelectorAll("button")].find(node => node.textContent.trim() === label);
      assert.ok(button, `Missing button: ${label}`);
      button.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    }),
    unmount: async () => {
      await act(async () => root.unmount());
      container.remove();
    },
  };
}

test("signed-out direct profile visit goes to sign-in", async () => {
  const ui = await renderProfile(null, async () => { throw new Error("Unexpected API call"); });
  try {
    assert.match(ui.container.textContent, /Sign in route/);
    assert.doesNotMatch(ui.container.textContent, /Account details/);
  } finally {
    await ui.unmount();
  }
});

test("two profiles show only their own email through request and acceptance", async () => {
  let requestSent = false;
  let accepted = false;
  let activeUserId = 1;
  const fetcher = async (url, options = {}) => {
    const path = new URL(url).pathname;
    let data;
    if (path === "/users/me/friends") data = accepted
      ? [{ id: activeUserId === 1 ? 2 : 1, username: activeUserId === 1 ? "Bob" : "Alice" }]
      : [];
    else if (path === "/users/me/friend-requests/11/accept" && options.method === "POST") {
      accepted = true;
      data = { id: 11, status: "accepted" };
    }
    else if (path === "/users/me/friend-requests") {
      if (options.method === "POST") {
        requestSent = true;
        data = { id: 11, status: "pending" };
      } else data = {
        incoming: requestSent && !accepted && activeUserId === 2 ? [{ id: 11, user: { id: 1, username: "Alice" } }] : [],
        outgoing: requestSent && !accepted && activeUserId === 1 ? [{ id: 11, user: { id: 2, username: "Bob" } }] : [],
      };
    }
    else if (path === "/users/me/blocks") data = [];
    else if (path === "/users/search") data = [{ id: 2, username: "Bob" }];
    else throw new Error(`Unexpected API call: ${url}`);
    return { ok: true, status: 200, json: async () => data };
  };
  const ui = await renderProfile({ id: 1, username: "Alice", email: "alice@example.com" }, fetcher);
  try {
    assert.match(ui.container.textContent, /alice@example\.com/);
    assert.doesNotMatch(ui.container.textContent, /bob@example\.com/);
    const input = ui.container.querySelector("#friend-search");
    await act(async () => {
      input.focus();
      const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
      setter.call(input, "Bob");
      input.dispatchEvent(new window.Event("input", { bubbles: true }));
      input.dispatchEvent(new window.Event("change", { bubbles: true }));
    });
    await ui.click("Search");
    assert.match(ui.container.textContent, /Bob/);
    await ui.click("Add friend");
    assert.equal(requestSent, true);
    assert.match(ui.container.textContent, /Request sent/);
  } finally {
    await ui.unmount();
  }
  activeUserId = 2;
  const bob = await renderProfile({ id: 2, username: "Bob", email: "bob@example.com" }, fetcher);
  try {
    assert.match(bob.container.textContent, /bob@example\.com/);
    assert.doesNotMatch(bob.container.textContent, /alice@example\.com/);
    assert.match(bob.container.textContent, /Incoming requests 1/);
    await bob.click("Accept");
    assert.equal(accepted, true);
    assert.match(bob.container.textContent, /Alice added as a friend/);
    assert.match(bob.container.textContent, /Friends 1/);
  } finally {
    await bob.unmount();
  }
});

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
globalThis.MouseEvent = dom.window.MouseEvent;
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

let vite;
let AuthProvider;
let ProtectedRoute;

before(async () => {
  vite = await createServer({ server: { middlewareMode: true }, appType: "custom" });
  ({ AuthProvider } = await vite.ssrLoadModule("/src/auth/AuthContext.jsx"));
  ({ default: ProtectedRoute } = await vite.ssrLoadModule("/src/auth/ProtectedRoute.jsx"));
});

after(async () => {
  await vite?.close();
  dom.window.close();
});

async function renderProtected(fetcher) {
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  localStorage.setItem("token", "saved-token");
  globalThis.fetch = fetcher;
  await act(async () => {
    root.render(createElement(AuthProvider, null,
      createElement(MemoryRouter, { initialEntries: ["/profile"] },
        createElement(Routes, null,
          createElement(Route, { path: "/profile", element: createElement(ProtectedRoute, null, createElement("p", null, "Private profile")) }),
          createElement(Route, { path: "/login", element: createElement("p", null, "Login route") }),
        ),
      ),
    ));
  });
  return {
    container,
    clickRetry: async () => act(async () => {
      container.querySelector("button")?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    }),
    unmount: async () => {
      await act(async () => root.unmount());
      container.remove();
      localStorage.clear();
    },
  };
}

test("401 removes the invalid saved token and returns to login", async () => {
  const ui = await renderProtected(async () => ({ ok: false, status: 401 }));
  try {
    assert.equal(localStorage.getItem("token"), null);
    assert.match(ui.container.textContent, /Login route/);
  } finally {
    await ui.unmount();
  }
});

for (const [name, failingFetch] of [
  ["server failure", async () => ({ ok: false, status: 500 })],
  ["network failure", async () => { throw new TypeError("Failed to fetch"); }],
]) {
  test(`${name} keeps the saved token and can retry`, async () => {
    let requests = 0;
    const ui = await renderProtected(async (...args) => {
      requests += 1;
      if (requests === 1) return failingFetch(...args);
      return { ok: true, json: async () => ({ id: 7, username: "player" }) };
    });
    try {
      assert.equal(localStorage.getItem("token"), "saved-token");
      assert.match(ui.container.querySelector("[role=alert]")?.textContent || "", /retry/i);
      await ui.clickRetry();
      assert.equal(requests, 2);
      assert.match(ui.container.textContent, /Private profile/);
    } finally {
      await ui.unmount();
    }
  });
}

import assert from "node:assert/strict";
import { after, before, test } from "node:test";
import { JSDOM } from "jsdom";
import React, { act, createElement, useState } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter, Route, Routes, useLocation } from "react-router";
import { createServer } from "vite";

const dom = new JSDOM("<!doctype html><html><body></body></html>", { url: "http://localhost/" });
globalThis.window = dom.window;
globalThis.document = dom.window.document;
globalThis.MouseEvent = dom.window.MouseEvent;
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

let vite;
let AuthContext;
let ProtectedRoute;
let LoginPage;
let SignupPage;

before(async () => {
  vite = await createServer({ server: { middlewareMode: true }, appType: "custom" });
  ({ AuthContext } = await vite.ssrLoadModule("/src/auth/auth-context.js"));
  ({ default: ProtectedRoute } = await vite.ssrLoadModule("/src/auth/ProtectedRoute.jsx"));
  ({ default: LoginPage } = await vite.ssrLoadModule("/src/pages/Login/LoginPage.jsx"));
  ({ default: SignupPage } = await vite.ssrLoadModule("/src/pages/Login/SignupPage.jsx"));
});

after(async () => {
  await vite?.close();
  dom.window.close();
});

function Destination() {
  const location = useLocation();
  return createElement("p", { "data-testid": "destination" }, `${location.pathname}${location.search}${location.hash}`);
}

function TestAuth({ children }) {
  const [user, setUser] = useState(null);
  return createElement(AuthContext.Provider, {
    value: {
      user,
      loading: false,
      login: async () => setUser({ id: 7, username: "player" }),
      signup: async () => null,
    },
  }, children);
}

async function renderInvite() {
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  await act(async () => {
    root.render(createElement(TestAuth, null,
      createElement(MemoryRouter, { initialEntries: ["/game/42?invite=friend#chat"] },
        createElement(Routes, null,
          createElement(Route, { path: "/game/:sessionId", element: createElement(ProtectedRoute, null, createElement(Destination)) }),
          createElement(Route, { path: "/login", element: createElement(LoginPage) }),
          createElement(Route, { path: "/signup", element: createElement(SignupPage) }),
        ),
      ),
    ));
  });
  const click = async text => act(async () => {
    const button = [...container.querySelectorAll("button")].find(element => element.textContent.includes(text));
    assert.ok(button, `Missing button: ${text}`);
    button.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  });
  return {
    container,
    click,
    unmount: async () => {
      await act(async () => root.unmount());
      container.remove();
    },
  };
}

test("signed-out invite returns to its full destination after login", async () => {
  const ui = await renderInvite();
  try {
    assert.match(ui.container.textContent, /INITIATE ACCESS/);
    await ui.click("INITIATE ACCESS");
    assert.equal(ui.container.querySelector("[data-testid=destination]")?.textContent, "/game/42?invite=friend#chat");
  } finally {
    await ui.unmount();
  }
});

test("invite destination survives visiting signup and returning to login", async () => {
  const ui = await renderInvite();
  try {
    await ui.click("DON'T HAVE AN ACCOUNT?");
    assert.match(ui.container.textContent, /Already Have an account/);
    await ui.click("Already Have an account");
    await ui.click("INITIATE ACCESS");
    assert.equal(ui.container.querySelector("[data-testid=destination]")?.textContent, "/game/42?invite=friend#chat");
  } finally {
    await ui.unmount();
  }
});

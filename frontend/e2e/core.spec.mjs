import { expect, test } from "@playwright/test";

const api = "http://127.0.0.1:8765";
const password = "ValidPass1!";

function identity(suffix) {
  const username = `e2e${Date.now()}${suffix}`;
  return { username, email: `${username}@example.test`, password };
}

async function createAccount(request, user) {
  const response = await request.post(`${api}/users/`, { data: user });
  expect(response.status()).toBe(201);
  const login = await request.post(`${api}/users/login`, {
    data: { username: user.username, password },
  });
  expect(login.ok()).toBeTruthy();
  return (await login.json()).access_token;
}

async function signedInPage(browser, token) {
  const context = await browser.newContext();
  await context.addInitScript(value => localStorage.setItem("token", value), token);
  return { context, page: await context.newPage() };
}

test("sign up, sign in, play and save Sandbox, then reopen it", async ({ page }) => {
  const user = identity("solo");
  await page.goto("/signup");
  await page.getByPlaceholder("username").fill(user.username);
  await page.getByPlaceholder("email").fill(user.email);
  await page.locator('input[autocomplete="new-password"]').first().fill(password);
  await page.locator('input[autocomplete="new-password"]').last().fill(password);
  await page.getByRole("button", { name: "CREATE YOUR ACCOUNT" }).click();
  await expect(page).toHaveURL(/\/login$/);
  await page.getByPlaceholder("username").fill(user.username);
  await page.locator('input[autocomplete="current-password"]').fill(password);
  await page.getByRole("button", { name: "INITIATE ACCESS" }).click();
  await expect(page).toHaveURL(/127\.0\.0\.1:5174\/$/);

  await page.getByRole("button", { name: "Enter your Sandbox", exact: true }).first().click();
  await expect(page).toHaveURL(/\/game\/\d+$/);
  const gameURL = page.url();
  const terminal = page.getByRole("textbox", { name: "Terminal command" });
  await expect(terminal).toBeVisible();
  await terminal.fill("echo browser-smoke");
  await terminal.press("Enter");
  await expect(page.locator(".output")).toContainText("browser-smoke");
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.locator(".output")).toContainText("Game Saved");
  await page.getByRole("button", { name: "Exit", exact: true }).click();
  await expect(page).toHaveURL(/127\.0\.0\.1:5174\/$/);
  await page.goto(gameURL);
  await expect(page.getByRole("textbox", { name: "Terminal command" })).toBeVisible();
});

test("friends can request and join a private MiniGames session", async ({ request, browser }) => {
  const host = identity("host");
  const guest = identity("guest");
  const hostToken = await createAccount(request, host);
  const guestToken = await createAccount(request, guest);
  const first = await signedInPage(browser, hostToken);
  const second = await signedInPage(browser, guestToken);
  try {
    await first.page.goto("/profile");
    await first.page.getByPlaceholder("Enter a username").fill(guest.username);
    await first.page.getByRole("button", { name: "Search", exact: true }).click();
    await first.page.getByRole("button", { name: "Add friend" }).click();
    await expect(first.page.getByText("Request sent", { exact: true })).toBeVisible();

    await second.page.goto("/profile");
    await expect(second.page.getByText(host.username)).toBeVisible();
    await second.page.getByRole("button", { name: "Accept", exact: true }).click();
    await expect(second.page.getByText("Friends 1")).toBeVisible();

    await first.page.goto("/session-create");
    await first.page.getByLabel("Session name").fill(`Private ${host.username}`);
    await first.page.getByLabel("Who can join?").selectOption("private");
    await first.page.getByRole("button", { name: "Create session" }).click();
    await expect(first.page).toHaveURL(/\/game\/\d+$/);

    await second.page.goto(first.page.url());
    await second.page.getByRole("button", { name: "Request to join" }).click();
    await expect(second.page.getByText("waiting for host approval")).toBeVisible();
    await expect(first.page.getByText("Join requests")).toBeVisible({ timeout: 10000 });
    await first.page.getByRole("button", { name: "Accept", exact: true }).click();
    await second.page.getByRole("button", { name: "Try joining again" }).click();
    await expect(second.page.getByRole("button", { name: host.username })).toBeVisible();
  } finally {
    await first.context.close();
    await second.context.close();
  }
});

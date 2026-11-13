import type { Locator, Page } from "@playwright/test";

import { expect, test } from "../fixtures";
import { loginViaUi, registerUser } from "../helpers/users";

async function hitsGlobeAtCenter(page: Page, locator: Locator): Promise<boolean> {
  await expect(locator, `${locator} должен быть подключён к DOM для проверки центра`).toBeAttached();
  // An empty flex slot may have zero width: height is enough for its center.
  await expect
    .poll(async () => (await locator.boundingBox())?.height ?? 0, {
      message: `${locator} должен иметь положительную высоту для проверки центра`,
    })
    .toBeGreaterThan(0);
  const box = await locator.boundingBox();
  if (!box) {
    throw new Error(`Не удалось определить boundingBox для ${locator}`);
  }

  return page.evaluate(
    ([x, y]) => (document.elementFromPoint(x, y)?.closest(".persistent-globe") ?? null) !== null,
    [box.x + box.width / 2, box.y + box.height / 2],
  );
}

/**
 * E2E: the app-global globe background: the host face follows the route (flight login -> home,
 * journey form -> home).
 *
 * The check is structural (by `.persistent-globe` data attributes), deliberately WITHOUT depending
 * on WebGL/canvas: the host's CSS layer (framing + scrim) must work where WebGL is unavailable
 * too (a headless browser without a GPU); a canvas failure is isolated by a boundary inside the host itself.
 */
test.describe("Persistent globe", () => {
  test("грань хоста следует за маршрутом: login до входа, home после", async ({ page, request }) => {
    const { username, password } = await registerUser(request);
    const globe = page.locator(".persistent-globe");

    // Public face: on /login the host is mounted and framed for the login form.
    await page.goto("/login");
    await expect(globe).toHaveAttribute("data-screen", "login");
    await expect(globe).toHaveAttribute("data-visible", "true");

    // After login the host is NOT unmounted: the same node switches to the dashboard face.
    await loginViaUi(page, { login: username, password });
    await expect(globe).toHaveAttribute("data-screen", "home");
    await expect(globe).toHaveAttribute("data-visible", "true");
  });

  test("форма поездки — грань того же глобуса: уход на дашборд перелетает, а не пересоздаёт его", async ({
    authedPage,
  }) => {
    const globe = authedPage.locator(".persistent-globe");

    // The projects' desktop viewport (>=992px): the globe column beside the form is visible, with its own face.
    await authedPage.goto("/journeys/add");
    await expect(globe).toHaveAttribute("data-screen", "journeyAdd");
    await expect(globe).toHaveAttribute("data-visible", "true");
    const hostNode = await globe.elementHandle();

    await authedPage.getByRole("link", { name: "MyJourney" }).click();

    await expect(globe).toHaveAttribute("data-screen", "home");
    await expect(globe).toHaveAttribute("data-visible", "true");
    // The same DOM node as on the form: WebGL was not reloaded, hence the flight.
    expect(await hostNode?.evaluate((node) => node.isConnected)).toBe(true);
  });

  test("дашборд пропускает события через слот к глобусу, а шапка сохраняет их", async ({ authedPage }) => {
    const globe = authedPage.locator(".persistent-globe");

    await authedPage.goto("/home");
    await expect(globe, "На /home глобус должен переключиться на грань home").toHaveAttribute("data-screen", "home");
    await expect(globe, "На /home глобус должен принимать события указателя").toHaveAttribute("data-interactive", "true");

    expect(
      await hitsGlobeAtCenter(authedPage, authedPage.locator(".home-stage")),
      "Центр слота дашборда должен пропускать события к .persistent-globe",
    ).toBe(true);
    expect(
      await hitsGlobeAtCenter(authedPage, authedPage.getByRole("link", { name: "MyJourney" })),
      "Ссылка MyJourney в шапке должна сохранять события, не пропуская их к глобусу",
    ).toBe(false);
  });

  test("форма поездки пропускает события через слот к глобусу, а заголовок сохраняет их", async ({ authedPage }) => {
    const globe = authedPage.locator(".persistent-globe");

    await authedPage.goto("/journeys/add");
    await expect(globe, "На /journeys/add глобус должен переключиться на грань journeyAdd").toHaveAttribute(
      "data-screen",
      "journeyAdd",
    );
    await expect(globe, "На /journeys/add глобус должен принимать события указателя").toHaveAttribute(
      "data-interactive",
      "true",
    );

    expect(
      await hitsGlobeAtCenter(authedPage, authedPage.locator(".add-journey__globe-col")),
      "Центр колонки глобуса на форме поездки должен пропускать события к .persistent-globe",
    ).toBe(true);
    expect(
      await hitsGlobeAtCenter(authedPage, authedPage.getByRole("heading", { level: 1, name: "New journey" })),
      "Заголовок New journey должен сохранять события в колонке формы, не пропуская их к глобусу",
    ).toBe(false);
  });
});

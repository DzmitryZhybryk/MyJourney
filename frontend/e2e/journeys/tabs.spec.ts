import { expect, test } from "../fixtures";
import { createJourney, findCityId } from "../helpers/journeys";
import { getStoredAccessToken } from "../helpers/session";

/**
 * E2E: the Journeys tabs share one map, switched by clicks in the section panel.
 *
 * One journey via the API (Moscow -> London by plane), then the user walks the tabs the way the UI
 * offers: journey map -> movements map -> add form -> back. The map node is tagged once in the page;
 * the tag surviving every switch proves the tabs reuse one instance instead of remounting it. Covers
 * what jsdom cannot: the lazy map chunk, the real router and the scene published by each tab.
 *
 * The desktop viewport keeps the panel over the map, so the add form only hides the map.
 */

const MAP = ".journeys-map";
const MAP_TAG = "e2eSameMap";

test.describe("Journeys tabs", () => {
  test("вкладки переключаются по одной и той же карте, «Добавить» её прячет, возврат показывает", async ({
    authedPage,
    request,
  }) => {
    const token = (await getStoredAccessToken(authedPage)) ?? "";
    expect(token, "после логина ожидается access-токен в sessionStorage").not.toBe("");
    await createJourney(request, token, {
      originCityId: await findCityId(request, token, "Moscow"),
      destinationCityId: await findCityId(request, token, "London"),
      transportType: "air",
      traveledYear: 2020,
    });

    await authedPage.goto("/journeys");
    await expect(authedPage.locator(".world-map__city-dot")).toHaveCount(2);
    await authedPage.locator(MAP).evaluate((map, tag) => {
      (map as HTMLElement).dataset[tag] = "1";
    }, MAP_TAG);
    const isSameMap = () =>
      authedPage.locator(MAP).evaluate((map, tag) => (map as HTMLElement).dataset[tag] === "1", MAP_TAG);

    await authedPage.getByRole("link", { name: "Movements map" }).click();
    await expect(authedPage.locator(".movement-line")).toHaveCount(1);
    await expect(authedPage.locator("svg.world-map")).toHaveCount(1);
    expect(await isSameMap()).toBe(true);

    await authedPage.getByRole("link", { name: "+ Add journey" }).click();
    await expect(authedPage.locator(MAP)).toHaveClass(/journeys-map--hidden/u);
    expect(await isSameMap()).toBe(true);

    await authedPage.getByRole("link", { name: "Journeys map" }).click();
    await expect(authedPage.locator(MAP)).not.toHaveClass(/journeys-map--hidden/u);
    await expect(authedPage.locator(".world-map__city-dot")).toHaveCount(2);
    expect(await isSameMap()).toBe(true);
  });
});

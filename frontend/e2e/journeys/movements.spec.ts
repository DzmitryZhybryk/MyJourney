import { expect, test } from "../fixtures";
import { createJourney, findCityId } from "../helpers/journeys";
import { getStoredAccessToken } from "../helpers/session";

/**
 * E2E: the movements map (/journeys/movements) on the user's real data.
 *
 * Two journeys via the API (Moscow -> London by plane in 2019, London -> Paris by land in 2022);
 * the tab draws a line per route. Filters change the map: the transport type goes to the backend
 * as a request (`transportType`), the year window applies on the client, so a line vanishes with
 * no request. Covers the chain create -> DB -> GET /movements -> filters -> render that
 * unit/component tests cannot reach (the SQL selection and layout are real, jsdom cannot see them).
 *
 * The UI language is pinned in the playwright config (en), so control names are English.
 */

test.describe("Journeys movements map", () => {
  test.beforeEach(async ({ authedPage, request }) => {
    const token = (await getStoredAccessToken(authedPage)) ?? "";
    expect(token, "после логина ожидается access-токен в sessionStorage").not.toBe("");

    const moscowId = await findCityId(request, token, "Moscow");
    const londonId = await findCityId(request, token, "London");
    const parisId = await findCityId(request, token, "Paris");
    await createJourney(request, token, {
      originCityId: moscowId,
      destinationCityId: londonId,
      transportType: "air",
      traveledYear: 2019,
    });
    await createJourney(request, token, {
      originCityId: londonId,
      destinationCityId: parisId,
      transportType: "land",
      traveledYear: 2022,
    });

    await authedPage.goto("/journeys/movements");
  });

  test("каждый маршрут рисуется линией, фильтр транспорта убирает лишний", async ({ authedPage }) => {
    const lines = authedPage.locator(".movement-line");
    await expect(lines).toHaveCount(2);

    // Turn off the plane: the backend returns only the land route.
    await authedPage.locator(".movements-controls__chip", { hasText: "Air" }).click();
    await expect(lines).toHaveCount(1);

    // With no transport selected (all three are on by default) the map is empty and hints to pick at
    // least one.
    await authedPage.locator(".movements-controls__chip", { hasText: "Land" }).click();
    await authedPage.locator(".movements-controls__chip", { hasText: "Water" }).click();
    await expect(lines).toHaveCount(0);
    await expect(authedPage.getByText("Choose at least one transport")).toBeVisible();
  });

  test("окно лет скрывает поездки вне окна", async ({ authedPage }) => {
    const lines = authedPage.locator(".movement-line");
    await expect(lines).toHaveCount(2);

    // The window starts at 2022: the 2019 journey drops out of it.
    await authedPage.getByRole("button", { name: "From year" }).click();
    await authedPage.getByRole("textbox", { name: "From year" }).fill("2022");
    await authedPage.getByRole("textbox", { name: "From year" }).press("Enter");

    await expect(lines).toHaveCount(1);
  });
});

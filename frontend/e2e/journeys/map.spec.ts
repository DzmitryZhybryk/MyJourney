import { expect, test } from "../fixtures";
import { createJourney, findCityId } from "../helpers/journeys";
import { getStoredAccessToken } from "../helpers/session";

/**
 * E2E: the journey map on the user's real data.
 *
 * End-to-end path: find cities via geo search, create a journey via the API by their ids (the
 * backend checks the cities exist), open the index tab /journeys; the map fetches the aggregate
 * from the backend, draws visited cities as dots and labels them with names from geo. Covers the
 * chain search -> create -> DB -> GET /map -> resolve -> render that unit/component tests cannot reach.
 *
 * This is a sessionStorage-token flow, so it runs on webkit too: a same-origin goto keeps the
 * access token, and with a token in sessionStorage AuthContext does not bootstrap via the refresh
 * cookie (see isBootstrapping), so webkit's Secure-cookie-over-http limitation is irrelevant and no skip is needed.
 */

test.describe("Journeys map", () => {
  test("посещённая поездка появляется точками-городами на карте", async ({ authedPage, request }) => {
    const token = await getStoredAccessToken(authedPage);
    expect(token, "после логина ожидается access-токен в sessionStorage").not.toBeNull();
    const bearer = token ?? "";

    await createJourney(request, bearer, {
      originCityId: await findCityId(request, bearer, "Moscow"),
      destinationCityId: await findCityId(request, bearer, "London"),
      transportType: "air",
      traveledYear: 2020,
    });

    await authedPage.goto("/journeys");

    // The map is drawn and the journey (origin+destination) settled as two city dots: the data
    // really went through create -> GET /map -> render.
    await expect(authedPage.locator("svg.world-map")).toBeVisible();
    await expect(authedPage.locator(".world-map__city-dot")).toHaveCount(2);
  });
});

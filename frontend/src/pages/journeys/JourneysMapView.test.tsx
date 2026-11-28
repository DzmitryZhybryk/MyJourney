import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { GEO_CITIES, server } from "../../test/handlers";
import { renderJourneysTabs } from "../../test/journeysMap";
import { screen, waitFor } from "../../test/render";
import { countriesWithFill } from "../../test/worldMap";
import { MAP_TONE } from "./journeys-data";
import { JourneysMapView } from "./JourneysMapView";

// City dots are SVG <circle> without an accessible name (no role/text, it is graphics), so data
// reaching the map is observed via the marker class.
const CITY_DOT = ".world-map__city-dot";

const UNKNOWN_CITY_ID = "99999999-9999-4999-8999-999999999999";

/** A map with one visited country (RU) and the given cities. */
function respondWithRussianCities(cityIds: string[]): void {
  server.use(
    http.get("/v1/journeys/map/", () =>
      HttpResponse.json({
        countries: [
          {
            countryCode: "RU",
            cities: cityIds.map((cityId, index) => ({ cityId, latitude: 55 + index, longitude: 37, years: [2020] })),
          },
        ],
      }),
    ),
  );
}

/** The only visited country on the map, found by its fill (an SVG path has no accessible name). */
function visitedCountry(container: HTMLElement): SVGPathElement {
  const [path] = countriesWithFill(container, MAP_TONE.visited);
  if (!path) {
    throw new Error("Посещённая страна не найдена");
  }

  return path;
}

/** The tab draws on the section's shared map, so it is rendered under it. */
function renderJourneysMap() {
  return renderJourneysTabs([{ path: "/journeys", element: <JourneysMapView /> }]);
}

describe("JourneysMapView", () => {
  it("показывает индикатор загрузки, затем рисует города на карте", async () => {
    const { container } = renderJourneysMap();

    expect(screen.getByText("Loading your map…")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.queryByText("Loading your map…")).not.toBeInTheDocument();
    });
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(container.querySelectorAll(CITY_DOT).length).toBeGreaterThan(0);
  });

  it("на пустом наборе поездок показывает карту без городов и без ошибки", async () => {
    server.use(http.get("/v1/journeys/map/", () => HttpResponse.json({ countries: [] })));

    const { container } = renderJourneysMap();

    await waitFor(() => {
      expect(screen.queryByText("Loading your map…")).not.toBeInTheDocument();
    });
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(container.querySelectorAll(CITY_DOT)).toHaveLength(0);
  });

  it("на ошибке показывает алерт, а по «Try again» успешно перезагружает карту", async () => {
    server.use(http.get("/v1/journeys/map/", () => new HttpResponse(null, { status: 500 })));

    const { user, container } = renderJourneysMap();

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Couldn't load your journeys");

    // The next request succeeds: on retry the alert goes away and the map fills with cities.
    server.use(
      http.get("/v1/journeys/map/", () =>
        HttpResponse.json({
          countries: [
            {
              countryCode: "RU",
              cities: [{ cityId: GEO_CITIES[0].cityId, latitude: 55.75, longitude: 37.62, years: [2020] }],
            },
          ],
        }),
      ),
    );
    await user.click(screen.getByRole("button", { name: "Try again" }));

    await waitFor(() => {
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    });
    expect(container.querySelectorAll(CITY_DOT).length).toBeGreaterThan(0);
  });

  it("в тултипе страны — названия городов, полученные у geo", async () => {
    respondWithRussianCities([GEO_CITIES[0].cityId]);
    const { user, container } = renderJourneysMap();
    await waitFor(() => expect(container.querySelectorAll(CITY_DOT)).toHaveLength(1));

    await user.hover(visitedCountry(container));

    expect(await screen.findByText("Moscow")).toBeInTheDocument();
  });

  it("город, которого geo не знает, подписан как неизвестный, а не пропадает", async () => {
    respondWithRussianCities([GEO_CITIES[0].cityId, UNKNOWN_CITY_ID]);
    const { user, container } = renderJourneysMap();
    await waitFor(() => expect(container.querySelectorAll(CITY_DOT)).toHaveLength(2));

    await user.hover(visitedCountry(container));

    expect(await screen.findByText("Moscow")).toBeInTheDocument();
    expect(await screen.findByText("Unknown city")).toBeInTheDocument();
  });

  it("под картой — атрибуция GeoNames со ссылками на источник и лицензию", () => {
    renderJourneysMap();

    expect(screen.getByRole("link", { name: "GeoNames" })).toHaveAttribute("href", "https://www.geonames.org");
    expect(screen.getByRole("link", { name: "CC BY 4.0" })).toHaveAttribute(
      "href",
      "https://creativecommons.org/licenses/by/4.0/",
    );
  });
});

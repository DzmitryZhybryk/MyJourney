import { fireEvent } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { afterEach, describe, expect, it, vi } from "vitest";

import { WORLD_VIEW_BOX } from "../../components/worldProjection";
import { GEO_CITIES, MOVEMENTS_RESPONSE, server } from "../../test/handlers";
import { stubScreenLayout } from "../../test/layout";
import { renderJourneysTabs } from "../../test/journeysMap";
import { act, screen, waitFor } from "../../test/render";
import { MovementsMapView } from "./MovementsMapView";

// Arcs, dots and labels are SVG without accessible roles, so map data is observed by class.
const ARC = ".movement-line";
const DOT = ".movement-dot";
const ROUTE = ".movement-route";
const HIT_ZONE = ".movement-route__hit";

const UNKNOWN_CITY_ID = "99999999-9999-4999-8999-999999999999";

/** A tab under the section's shared map, which also hands it the panel ref. */
function renderMovements() {
  return renderJourneysTabs([{ path: "/journeys/movements", element: <MovementsMapView /> }]);
}

function viewBoxWidth(container: HTMLElement): number {
  return Number(container.querySelector(".world-map")?.getAttribute("viewBox")?.split(" ")[2]);
}

/** Records the query strings of movements map requests and answers with the unfiltered fixture. */
function recordMovementsRequests(): string[] {
  const queries: string[] = [];
  server.use(
    http.get("/v1/journeys/movements/", ({ request }) => {
      queries.push(new URL(request.url).searchParams.toString());
      return HttpResponse.json(MOVEMENTS_RESPONSE);
    }),
  );
  return queries;
}

/** One Tokyo -> Los Angeles route: the shortest path crosses the Pacific, over the 180th meridian. */
function stubTokyoToLosAngeles(): void {
  server.use(
    http.get("/v1/journeys/movements/", () =>
      HttpResponse.json({
        firstYear: 2020,
        lastYear: 2020,
        connections: [
          {
            origin: { cityId: GEO_CITIES[0].cityId, latitude: 35.69, longitude: 139.69 },
            destination: { cityId: GEO_CITIES[1].cityId, latitude: 34.05, longitude: -118.24 },
            years: [2020],
          },
        ],
      }),
    ),
  );
}

/** Waits until all three fixture routes appear on the map. */
async function waitForAllRoutes(container: HTMLElement): Promise<void> {
  await waitFor(() => {
    expect(container.querySelectorAll(ARC)).toHaveLength(3);
  });
}

describe("MovementsMapView", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("рисует дугу со стрелкой на каждый маршрут и точку на каждый город", async () => {
    const { container } = renderMovements();

    expect(screen.getByText("Loading your map…")).toBeInTheDocument();
    await waitForAllRoutes(container);

    // Moscow <-> London is two routes, London -> Paris the third; each has an arrow at the end.
    for (const arc of container.querySelectorAll(ARC)) {
      expect(arc.getAttribute("marker-end")).toBe("url(#movement-arrow)");
    }

    expect(container.querySelectorAll(DOT)).toHaveLength(3);
    expect(screen.queryByText("Loading your map…")).not.toBeInTheDocument();
  });

  it("дуга через край мира — два куска, гаснущих у разреза, стрелка только на втором", async () => {
    stubTokyoToLosAngeles();

    const { container } = renderMovements();

    // Each piece has a tail at the cut fading by a gradient, and the rest is solid.
    await waitFor(() => {
      expect(container.querySelectorAll(ARC)).toHaveLength(4);
    });
    const arcs = [...container.querySelectorAll<SVGPathElement>(ARC)];
    const fading = arcs.filter((arc) => arc.style.stroke.startsWith("url("));
    expect(fading).toHaveLength(2);
    expect(container.querySelectorAll("linearGradient")).toHaveLength(2);
    // There is one arrow, at the end of the second piece's solid part, at the destination point.
    const withArrow = arcs.filter((arc) => arc.getAttribute("marker-end") === "url(#movement-arrow)");
    expect(withArrow).toEqual([arcs[3]]);
    expect(arcs[3].style.stroke).toBe("");
  });

  it("у каждого маршрута есть зона наведения в одной группе с его линией", async () => {
    const { container } = renderMovements();
    await waitForAllRoutes(container);

    const routes = container.querySelectorAll(ROUTE);
    expect(routes).toHaveLength(3);
    for (const route of routes) {
      expect(route.querySelectorAll(ARC)).toHaveLength(1);
      expect(route.querySelectorAll(HIT_ZONE)).toHaveLength(1);
    }
  });

  it("дуга через край мира подсвечивается целиком: обе зоны наведения в одной группе со всеми кусками линии", async () => {
    stubTokyoToLosAngeles();
    const { container } = renderMovements();

    await waitFor(() => {
      expect(container.querySelectorAll(ROUTE)).toHaveLength(1);
    });
    const [route] = container.querySelectorAll(ROUTE);
    expect(route.querySelectorAll(HIT_ZONE)).toHaveLength(2);
    expect(route.querySelectorAll(ARC)).toHaveLength(4);
  });

  it("подписывает города их названиями и указывает источник названий", async () => {
    renderMovements();

    for (const { name } of GEO_CITIES) {
      expect(await screen.findByText(name)).toBeInTheDocument();
    }

    expect(screen.getByRole("link", { name: "GeoNames" })).toHaveAttribute("href", "https://www.geonames.org");
  });

  it("город, которого нет в справочнике, подписан «Unknown city»", async () => {
    const [moscow] = GEO_CITIES;
    server.use(
      http.get("/v1/journeys/movements/", () =>
        HttpResponse.json({
          firstYear: 2020,
          lastYear: 2020,
          connections: [
            {
              origin: { cityId: moscow.cityId, latitude: moscow.latitude, longitude: moscow.longitude },
              destination: { cityId: UNKNOWN_CITY_ID, latitude: 40, longitude: 20 },
              years: [2020],
            },
          ],
        }),
      ),
    );

    renderMovements();

    expect(await screen.findByText("Unknown city")).toBeInTheDocument();
    expect(screen.getByText("Moscow")).toBeInTheDocument();
  });

  it("открывается приближенной к маршрутам, а не всем миром", async () => {
    stubScreenLayout({
      "world-map": { left: 0, top: 0, width: 1000, height: 487 },
      "world-map-canvas": { left: 0, top: 0, width: 1000, height: 487 },
      "world-map-wrap": { left: 0, top: 0, width: 1000, height: 487 },
    });

    const { container } = renderMovements();

    await waitFor(() => {
      expect(viewBoxWidth(container)).toBeLessThan(WORLD_VIEW_BOX.width);
    });
  });

  it("без поездок показывает подсказку и пустую карту", async () => {
    server.use(
      http.get("/v1/journeys/movements/", () => HttpResponse.json({ firstYear: null, lastYear: null, connections: [] })),
    );

    const { container } = renderMovements();

    expect(await screen.findByText("No journeys yet — add one and your routes will show up here")).toBeInTheDocument();
    expect(container.querySelectorAll(ARC)).toHaveLength(0);
    expect(viewBoxWidth(container)).toBe(WORLD_VIEW_BOX.width);
  });

  it("на ошибке показывает алерт, а «Try again» перезагружает маршруты", async () => {
    server.use(http.get("/v1/journeys/movements/", () => new HttpResponse(null, { status: 500 })));

    const { user, container } = renderMovements();

    expect(await screen.findByRole("alert")).toHaveTextContent("Couldn't load your journeys");
    // There is no empty hint on an error: journeys may exist, they just failed to load.
    expect(screen.queryByText(/No journeys yet/u)).not.toBeInTheDocument();

    server.resetHandlers();
    await user.click(screen.getByRole("button", { name: "Try again" }));

    await waitForAllRoutes(container);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("по умолчанию показывает все годы и все виды транспорта", async () => {
    renderMovements();

    expect(await screen.findByRole("button", { name: "From year" })).toHaveTextContent("2019");
    expect(screen.getByRole("button", { name: "To year" })).toHaveTextContent("2022");
    for (const transport of ["Land", "Air", "Water"]) {
      expect(screen.getByRole("checkbox", { name: transport })).toBeChecked();
    }
  });

  it("окно лет фильтрует маршруты на клиенте — без запросов", async () => {
    const queries = recordMovementsRequests();
    const { user, container } = renderMovements();
    await waitForAllRoutes(container);
    const toYear = screen.getByRole("slider", { name: "To year" });

    // Focus as from the keyboard (Tab): in jsdom a click would start a drag on a zero-width track.
    act(() => toYear.focus());
    await user.keyboard("{ArrowLeft}");

    // Window 2019-2021: London -> Paris (2022) is gone, Moscow <-> London remain.
    await waitFor(() => {
      expect(container.querySelectorAll(ARC)).toHaveLength(2);
    });
    expect(screen.getByRole("button", { name: "To year" })).toHaveTextContent("2021");
    expect(queries).toEqual([""]);
  });

  it("карта меняется прямо во время перетаскивания ползунка, до отпускания кнопки", async () => {
    // The slider track is 300 px: 2019 at the left edge, 2022 at the right, a year is 100 px.
    stubScreenLayout({ "mantine-RangeSlider-trackContainer": { left: 0, top: 0, width: 300, height: 20 } });
    const queries = recordMovementsRequests();
    const { container } = renderMovements();
    await waitForAllRoutes(container);
    const track = container.querySelector(".mantine-RangeSlider-trackContainer");
    if (!track) {
      throw new Error("Дорожка ползунка не найдена");
    }

    // Grab the right thumb and drag left by a year without releasing the button.
    fireEvent.mouseDown(track, { clientX: 300, clientY: 10 });
    fireEvent.mouseMove(document, { clientX: 200, clientY: 10 });

    await waitFor(() => {
      expect(container.querySelectorAll(ARC)).toHaveLength(2);
    });
    expect(queries).toEqual([""]);

    fireEvent.mouseUp(document);
  });

  it("вписанный год переставляет ручку, а год за пределами встаёт на границу", async () => {
    const { user, container } = renderMovements();
    await waitForAllRoutes(container);

    await user.click(screen.getByRole("button", { name: "From year" }));
    await user.clear(screen.getByRole("textbox", { name: "From year" }));
    await user.type(screen.getByRole("textbox", { name: "From year" }), "2021{Enter}");

    // Window 2021-2022: London -> Moscow (2020) is gone.
    await waitFor(() => {
      expect(container.querySelectorAll(ARC)).toHaveLength(2);
    });
    expect(screen.getByRole("button", { name: "From year" })).toHaveTextContent("2021");

    // 200 is below the first year of the scale: the left bound snaps to 2019.
    await user.click(screen.getByRole("button", { name: "From year" }));
    await user.clear(screen.getByRole("textbox", { name: "From year" }));
    await user.type(screen.getByRole("textbox", { name: "From year" }), "200{Enter}");

    expect(await screen.findByRole("button", { name: "From year" })).toHaveTextContent("2019");
    await waitForAllRoutes(container);
  });

  it("левый год нельзя вписать правее правого — он встаёт вровень с ним", async () => {
    const { user, container } = renderMovements();
    await waitForAllRoutes(container);
    const toYear = screen.getByRole("slider", { name: "To year" });
    act(() => toYear.focus());
    await user.keyboard("{ArrowLeft}{ArrowLeft}");

    await user.click(screen.getByRole("button", { name: "From year" }));
    await user.clear(screen.getByRole("textbox", { name: "From year" }));
    await user.type(screen.getByRole("textbox", { name: "From year" }), "2022{Enter}");

    expect(await screen.findByRole("button", { name: "From year" })).toHaveTextContent("2020");
  });

  it("Escape и пустое поле оставляют прежний год", async () => {
    const { user, container } = renderMovements();
    await waitForAllRoutes(container);

    await user.click(screen.getByRole("button", { name: "To year" }));
    await user.type(screen.getByRole("textbox", { name: "To year" }), "{Backspace}0{Escape}");
    expect(await screen.findByRole("button", { name: "To year" })).toHaveTextContent("2022");

    await user.click(screen.getByRole("button", { name: "To year" }));
    await user.clear(screen.getByRole("textbox", { name: "To year" }));
    await user.keyboard("{Enter}");
    expect(await screen.findByRole("button", { name: "To year" })).toHaveTextContent("2022");
  });

  it("снятый вид транспорта убирает его из запроса, а без транспорта карта пуста и запроса нет", async () => {
    const queries = recordMovementsRequests();
    const { user, container } = renderMovements();
    await waitForAllRoutes(container);

    await user.click(screen.getByRole("checkbox", { name: "Water" }));
    await waitFor(() => {
      expect(queries.at(-1)).toBe("transportType=air&transportType=land");
    });

    await user.click(screen.getByRole("checkbox", { name: "Air" }));
    await user.click(screen.getByRole("checkbox", { name: "Land" }));

    expect(await screen.findByText("Choose at least one transport")).toBeInTheDocument();
    expect(container.querySelectorAll(ARC)).toHaveLength(0);
    // No request went out without the transport filter.
    expect(queries.filter((query) => query.includes("transportType="))).toEqual([
      "transportType=air&transportType=land",
      "transportType=land",
    ]);
  });

  it("засечки лет не теснее 10 px: за полвека на узком ползунке — через год, а не каждый год", async () => {
    server.use(
      http.get("/v1/journeys/movements/", () =>
        HttpResponse.json({ ...MOVEMENTS_RESPONSE, firstYear: 1976, lastYear: 2026 }),
      ),
    );
    // A 300 px slider over 50 years is about 6 px per year: a tick every year would blur into beads.
    stubScreenLayout({ "movements-controls__slider": { left: 0, top: 0, width: 300, height: 30 } });

    const { container } = renderMovements();

    await screen.findByRole("slider", { name: "To year" });
    // A step of 2 years: even years from 1976 to 2026 give 26 ticks instead of 51.
    await waitFor(() => {
      expect(container.querySelectorAll(".mantine-RangeSlider-mark")).toHaveLength(26);
    });
  });

  it("поездки одного года — подпись года без ползунка", async () => {
    server.use(
      http.get("/v1/journeys/movements/", () =>
        HttpResponse.json({ ...MOVEMENTS_RESPONSE, firstYear: 2020, lastYear: 2020 }),
      ),
    );

    renderMovements();

    expect(await screen.findByText("2020")).toBeInTheDocument();
    expect(screen.queryByRole("slider")).not.toBeInTheDocument();
  });
});

import { delay, http, HttpResponse } from "msw";
import { useEffect } from "react";
import { useNavigate } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import { getJourneysGlobeQueryKey } from "../../api/sdk";
import { i18n } from "../../i18n";
import enCommon from "../../locales/en/common.json";
import ruCommon from "../../locales/ru/common.json";
import { GEO_CITIES, server } from "../../test/handlers";
import { act, createTestQueryClient, makeAuthValue, renderWithProviders, screen, waitFor } from "../../test/render";
import type { AuthContextValue } from "../../auth/useAuth";
import type { GlobePov } from "./GlobeCanvas";
import { useGlobeSceneActions, type GlobeSlot } from "./globeScene";
import { PersistentGlobeHost } from "./PersistentGlobeHost";
import { routeCameraPov, type GlobeRoute } from "./route";
import { ROUTE_CITIES } from "./routes";

/*
 * The canvas is mocked: it pulls in three/WebGL, which jsdom lacks. The mock reflects the passed
 * props into data attributes so the test checks WHAT the host feeds the globe (arc/city counts,
 * pause) without touching WebGL itself. The canvas is lazy in the host, hence the wait via `findByTestId`.
 */
type MockGlobeProps = {
  arcs?: readonly unknown[];
  labelCities?: readonly { name?: string }[];
  paused?: boolean;
  interactive?: boolean;
  autoRotate?: boolean;
  route?: GlobeRoute | null;
  routeFading?: boolean;
  pov?: GlobePov;
  reveal?: boolean;
};

vi.mock("./GlobeCanvas", () => ({
  GlobeCanvas: ({ arcs, labelCities, paused, interactive, autoRotate, route, routeFading, pov, reveal }: MockGlobeProps) => (
    <div
      data-testid="globe-canvas"
      data-arcs={arcs?.length ?? 0}
      data-cities={labelCities?.length ?? 0}
      data-city-names={labelCities?.map((city) => city.name ?? "∅").join("|") ?? ""}
      data-paused={String(paused ?? false)}
      data-interactive={String(interactive ?? false)}
      data-auto-rotate={String(autoRotate ?? true)}
      data-route={route ? route.originLabel : "none"}
      data-route-fading={String(routeFading ?? false)}
      data-pov-lat={pov?.lat}
      data-pov-altitude={pov?.altitude}
      data-reveal={String(reveal ?? false)}
    />
  ),
}));

/*
 * The scene publisher is what the add-journey page does in production: it puts the form route and
 * the column rectangle into the channel. It lives OUTSIDE the routes, so leaving /journeys/add
 * does not unmount it: after navigation the scene still holds the route, as in that single
 * render when the page has not cleared it yet.
 */
function ScenePublisher({ route, slot }: { route: GlobeRoute | null; slot: GlobeSlot | null }) {
  const { setRoute, setSlot } = useGlobeSceneActions();
  useEffect(() => {
    setRoute(route);
    setSlot(slot);
  }, [route, slot, setRoute, setSlot]);

  return null;
}

/** An in-app navigation button: leaving the form face the way a user does. */
function GoTo({ path }: { path: string }) {
  const navigate = useNavigate();
  return (
    <button type="button" onClick={() => navigate(path)}>
      {`go ${path}`}
    </button>
  );
}

/** AuthContext of a logged-in user with the given `sub` (cities are cached by it). */
function authedValue(sub: string): AuthContextValue {
  return makeAuthValue({ isAuthenticated: true, claims: { sub, email_verified: true, exp: 4_102_444_800 } });
}

function screenAttr(container: HTMLElement, attr: string): string | null {
  return container.querySelector(".persistent-globe")?.getAttribute(attr) ?? null;
}

describe("PersistentGlobeHost — грань по маршруту", () => {
  it.each([
    { route: "/", screen: "landing" },
    { route: "/login", screen: "login" },
    { route: "/signup", screen: "signup" },
    { route: "/whatever", screen: "landing" },
  ])("на $route ставит data-screen=$screen", ({ route, screen: expected }) => {
    const { container } = renderWithProviders(<PersistentGlobeHost />, { route, authValue: makeAuthValue() });

    expect(screenAttr(container, "data-screen")).toBe(expected);
  });

  it("на /home (залогинен) ставит грань home и держит глобус видимым", () => {
    const { container } = renderWithProviders(<PersistentGlobeHost />, {
      route: "/home",
      authValue: authedValue("user-1"),
    });

    expect(screenAttr(container, "data-screen")).toBe("home");
    expect(screenAttr(container, "data-visible")).toBe("true");
  });

  it("на /journeys прячет глобус (data-visible=false, грань остаётся home)", () => {
    const { container } = renderWithProviders(<PersistentGlobeHost />, {
      route: "/journeys",
      authValue: authedValue("user-1"),
    });

    expect(screenAttr(container, "data-screen")).toBe("home");
    expect(screenAttr(container, "data-visible")).toBe("false");
  });

  it.each([
    { route: "/home", interactive: "true" },
    { route: "/", interactive: "false" },
    { route: "/login", interactive: "false" },
    { route: "/signup", interactive: "false" },
    { route: "/journeys", interactive: "false" },
  ])("драг-вращение: на $route data-interactive=$interactive", ({ route, interactive }) => {
    const { container } = renderWithProviders(<PersistentGlobeHost />, {
      route,
      authValue: authedValue("user-1"),
    });

    expect(screenAttr(container, "data-interactive")).toBe(interactive);
  });
});

describe("PersistentGlobeHost — источник данных глобуса", () => {
  it("аноним получает курируемые дуги и города", async () => {
    renderWithProviders(<PersistentGlobeHost />, { route: "/", authValue: makeAuthValue() });

    const globe = await screen.findByTestId("globe-canvas");

    expect(Number(globe.getAttribute("data-arcs"))).toBeGreaterThan(0);
    expect(Number(globe.getAttribute("data-cities"))).toBeGreaterThan(0);
    expect(globe).toHaveAttribute("data-paused", "false");
  });

  it("курируемые города аноним видит на языке интерфейса, смена языка их переподписывает", async () => {
    i18n.addResourceBundle("ru", "common", ruCommon, true, true);
    const namesIn = (cities: Record<string, string>) => ROUTE_CITIES.map((city) => cities[city.id]).join("|");
    try {
      renderWithProviders(<PersistentGlobeHost />, { route: "/", authValue: makeAuthValue() });

      const globe = await screen.findByTestId("globe-canvas");
      expect(globe).toHaveAttribute("data-city-names", namesIn(enCommon.globe.cities));

      await act(async () => {
        await i18n.changeLanguage("ru");
      });

      expect(globe).toHaveAttribute("data-city-names", namesIn(ruCommon.globe.cities));
    } finally {
      await act(async () => {
        await i18n.changeLanguage("en");
      });
    }
  });

  it("залогиненный получает реальные города без дуг (fade-in по приходе /journeys/globe)", async () => {
    renderWithProviders(<PersistentGlobeHost />, { route: "/home", authValue: authedValue("user-1") });

    const globe = await screen.findByTestId("globe-canvas");

    // An authenticated user has no arcs; cities arrive asynchronously from journeys/globe (Moscow + London).
    expect(globe).toHaveAttribute("data-arcs", "0");
    // The dashboard is the only face where the canvas gets interactive (drag rotation).
    expect(globe).toHaveAttribute("data-interactive", "true");
    await waitFor(() => expect(globe).toHaveAttribute("data-cities", "2"));
  });

  it("подписи городов — названия из geo", async () => {
    renderWithProviders(<PersistentGlobeHost />, { route: "/home", authValue: authedValue("user-1") });

    const globe = await screen.findByTestId("globe-canvas");

    await waitFor(() => expect(globe).toHaveAttribute("data-city-names", "Moscow|London"));
  });

  it("город, которого geo не знает, подписан как неизвестный, а не пропадает", async () => {
    server.use(
      http.get("/v1/journeys/globe/", () =>
        HttpResponse.json({
          cities: [
            { cityId: GEO_CITIES[0].cityId, latitude: 55.75, longitude: 37.62 },
            { cityId: "99999999-9999-4999-8999-999999999999", latitude: 1, longitude: 2 },
          ],
        }),
      ),
    );
    renderWithProviders(<PersistentGlobeHost />, { route: "/home", authValue: authedValue("user-1") });

    const globe = await screen.findByTestId("globe-canvas");

    await waitFor(() => expect(globe).toHaveAttribute("data-city-names", "Moscow|Unknown city"));
  });

  it("пока названия грузятся, города видны точками без подписи", async () => {
    server.use(
      http.post("/v1/geo/cities/resolve/", async () => {
        await delay("infinite");
        return HttpResponse.json({ items: [] });
      }),
    );
    // The names request goes out only once the globe points are received; wait for exactly that.
    let resolveRequests = 0;
    server.events.on("request:start", ({ request }) => {
      if (new URL(request.url).pathname === "/v1/geo/cities/resolve/") {
        resolveRequests += 1;
      }
    });
    renderWithProviders(<PersistentGlobeHost />, { route: "/home", authValue: authedValue("user-1") });

    const globe = await screen.findByTestId("globe-canvas");

    await waitFor(() => expect(resolveRequests).toBe(1));
    expect(globe).toHaveAttribute("data-city-names", "∅|∅");
    server.events.removeAllListeners();
  });

  it("сбой загрузки названий не стирает точки городов", async () => {
    server.use(http.post("/v1/geo/cities/resolve/", () => new HttpResponse(null, { status: 500 })));

    renderWithProviders(<PersistentGlobeHost />, { route: "/home", authValue: authedValue("user-1") });

    const globe = await screen.findByTestId("globe-canvas");

    await waitFor(() => expect(globe).toHaveAttribute("data-city-names", "∅|∅"));
  });

  it("ошибка загрузки городов не роняет глобус — остаётся без точек", async () => {
    server.use(http.get("/v1/journeys/globe/", () => HttpResponse.error()));

    renderWithProviders(<PersistentGlobeHost />, { route: "/home", authValue: authedValue("user-1") });

    const globe = await screen.findByTestId("globe-canvas");

    expect(globe).toHaveAttribute("data-cities", "0");
  });

  it("на /journeys глобус на паузе (рендер остановлен)", async () => {
    renderWithProviders(<PersistentGlobeHost />, { route: "/journeys", authValue: authedValue("user-1") });

    const globe = await screen.findByTestId("globe-canvas");

    expect(globe).toHaveAttribute("data-paused", "true");
  });
});

describe("PersistentGlobeHost — свежесть данных фона", () => {
  /**
   * Counts globe requests and returns cities with the given names. Cities come from the gazetteer
   * fixture, whose ids the fake `resolve` knows, so the points get names.
   */
  function countGlobeRequests(cityNames: string[]): () => number {
    let requests = 0;
    const cities = cityNames.map((name) => GEO_CITIES.find((city) => city.name === name));
    server.use(
      http.get("/v1/journeys/globe/", () => {
        requests += 1;
        return HttpResponse.json({
          cities: cities.map((city) => ({
            cityId: city?.cityId,
            latitude: city?.latitude,
            longitude: city?.longitude,
          })),
        });
      }),
    );

    return () => requests;
  }

  it("возврат на грань не перезапрашивает города — фон живёт со снимка (staleTime: Infinity)", async () => {
    const requestCount = countGlobeRequests(["Moscow", "Paris"]);
    const queryClient = createTestQueryClient();
    const options = { route: "/home", authValue: authedValue("user-1"), queryClient };

    const first = renderWithProviders(<PersistentGlobeHost />, options);
    await waitFor(() => expect(screen.getByTestId("globe-canvas")).toHaveAttribute("data-cities", "2"));
    first.unmount();

    renderWithProviders(<PersistentGlobeHost />, options);

    // The points are in place at once, from the cache, and there was no second request.
    expect(await screen.findByTestId("globe-canvas")).toHaveAttribute("data-cities", "2");
    expect(requestCount()).toBe(1);
  });

  it("инвалидация ключа глобуса обновляет фон, несмотря на бесконечную свежесть", async () => {
    // This is how a journey added in the form reaches the globe: `staleTime: Infinity` alone would
    // never refresh, so the mutation invalidates the globe key.
    const requestCount = countGlobeRequests(["Moscow"]);
    const queryClient = createTestQueryClient();
    renderWithProviders(<PersistentGlobeHost />, {
      route: "/home",
      authValue: authedValue("user-1"),
      queryClient,
    });
    await waitFor(() => expect(screen.getByTestId("globe-canvas")).toHaveAttribute("data-cities", "1"));

    countGlobeRequests(["Moscow", "London"]);
    await act(async () => {
      await queryClient.invalidateQueries({ queryKey: getJourneysGlobeQueryKey() });
    });

    await waitFor(() => expect(screen.getByTestId("globe-canvas")).toHaveAttribute("data-cities", "2"));
    expect(requestCount()).toBe(1);
  });

  it("аноним карту не запрашивает вовсе", async () => {
    const requestCount = countGlobeRequests(["Moscow"]);

    renderWithProviders(<PersistentGlobeHost />, { route: "/", authValue: makeAuthValue() });

    await screen.findByTestId("globe-canvas");
    expect(requestCount()).toBe(0);
  });
});

describe("PersistentGlobeHost — каркас без WebGL", () => {
  it("рисует stage и scrim и скрыт от скринридера (aria-hidden)", () => {
    const { container } = renderWithProviders(<PersistentGlobeHost />, { route: "/", authValue: makeAuthValue() });

    expect(container.querySelector(".persistent-globe__stage")).not.toBeNull();
    expect(container.querySelector(".persistent-globe__scrim")).not.toBeNull();
    expect(container.querySelector(".persistent-globe")).toHaveAttribute("aria-hidden");
  });
});

describe("PersistentGlobeHost — грань формы поездки", () => {
  const [MOSCOW, LONDON] = GEO_CITIES;
  const ROUTE: GlobeRoute = {
    origin: MOSCOW,
    destination: LONDON,
    transportType: "air",
    originLabel: "Moscow",
    destinationLabel: "London",
  };
  // jsdom: the viewport is 1024x768. The column is on the right, as in the desktop form layout.
  const SLOT: GlobeSlot = { left: 700, top: 100, width: 300, height: 600 };

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  function renderJourneyAdd(options: { slot?: GlobeSlot | null; route?: GlobeRoute | null; queryClient?: ReturnType<typeof createTestQueryClient> } = {}) {
    const { slot = SLOT, route = ROUTE, queryClient } = options;
    return renderWithProviders(
      <>
        <ScenePublisher route={route} slot={slot} />
        <GoTo path="/home" />
        <GoTo path="/journeys" />
        <GoTo path="/login" />
        <PersistentGlobeHost />
      </>,
      { route: "/journeys/add", authValue: authedValue("user-1"), queryClient },
    );
  }

  it("с колонкой — грань journeyAdd: глобус видим, крутится рукой, не на паузе", async () => {
    const { container } = renderJourneyAdd();

    await waitFor(() => expect(screenAttr(container, "data-screen")).toBe("journeyAdd"));
    expect(screenAttr(container, "data-visible")).toBe("true");
    expect(screenAttr(container, "data-interactive")).toBe("true");
    expect(await screen.findByTestId("globe-canvas")).toHaveAttribute("data-paused", "false");
  });

  it("пустая форма — глобус медленно вращается, как на дашборде", async () => {
    renderJourneyAdd({ route: { ...ROUTE, origin: null, destination: null } });

    const globe = await screen.findByTestId("globe-canvas");

    await waitFor(() => expect(globe).toHaveAttribute("data-auto-rotate", "true"));
  });

  it.each([
    { case: "выбран город отправления", origin: MOSCOW, destination: null },
    { case: "выбран только город назначения", origin: null, destination: LONDON },
  ])("$case — вращение стоит: камера кадрирует маршрут", async ({ origin, destination }) => {
    renderJourneyAdd({ route: { ...ROUTE, origin, destination } });

    const globe = await screen.findByTestId("globe-canvas");

    await waitFor(() => expect(globe).toHaveAttribute("data-route", "Moscow"));
    expect(globe).toHaveAttribute("data-auto-rotate", "false");
  });

  it("на грани формы камера появляется подлётом издалека, на дашборде — сразу на месте", async () => {
    const { user } = renderJourneyAdd({ route: { ...ROUTE, origin: null, destination: null } });
    const globe = await screen.findByTestId("globe-canvas");

    await waitFor(() => expect(globe).toHaveAttribute("data-reveal", "true"));

    await user.click(screen.getByRole("button", { name: "go /home" }));
    expect(globe).toHaveAttribute("data-reveal", "false");
  });

  it("без колонки (узкий экран) — глобус спрятан, на паузе и не ловит жесты", async () => {
    const { container } = renderJourneyAdd({ slot: null });

    const globe = await screen.findByTestId("globe-canvas");

    expect(screenAttr(container, "data-visible")).toBe("false");
    expect(screenAttr(container, "data-interactive")).toBe("false");
    expect(globe).toHaveAttribute("data-paused", "true");
    expect(globe).toHaveAttribute("data-route", "none");
  });

  it("на грани формы — только маршрут: посещённые города не рисуются", async () => {
    const queryClient = createTestQueryClient();
    queryClient.setQueryData(getJourneysGlobeQueryKey(), {
      cities: [{ cityId: GEO_CITIES[2].cityId, latitude: 48.85, longitude: 2.35 }],
    });
    renderJourneyAdd({ queryClient });

    const globe = await screen.findByTestId("globe-canvas");

    await waitFor(() => expect(globe).toHaveAttribute("data-route", "Moscow"));
    expect(globe).toHaveAttribute("data-cities", "0");
  });

  it("камера кадрирует маршрут формы, а не грань дашборда", async () => {
    renderJourneyAdd();

    const globe = await screen.findByTestId("globe-canvas");

    await waitFor(() => expect(globe).toHaveAttribute("data-pov-lat", String(routeCameraPov(ROUTE).lat)));
  });

  it("кадрирует и обрезает сферу по прямоугольнику колонки", async () => {
    const { container } = renderJourneyAdd();
    const host = container.querySelector<HTMLElement>(".persistent-globe");

    await waitFor(() => expect(host?.style.getPropertyValue("--globe-slot-clip")).not.toBe(""));
    // Clip insets from the viewport edges: right 1024 - (700 + 300), bottom 768 - (100 + 600).
    expect(host?.style.getPropertyValue("--globe-slot-clip")).toBe("inset(100px 24px 68px 700px)");
    // Column center (850, 400) minus viewport center (512, 384).
    expect(host?.style.getPropertyValue("--globe-slot-x")).toBe("338px");
    expect(host?.style.getPropertyValue("--globe-slot-y")).toBe("16px");
    // The face has no scale of its own: it is shared with the dashboard (CSS), otherwise the transition would resize.
    expect(host?.style.getPropertyValue("--globe-slot-scale")).toBe("");
  });

  it("без маршрута камера формы на высоте дашборда — уход на /home не меняет размер сферы", async () => {
    const queryClient = createTestQueryClient();
    const home = renderWithProviders(<PersistentGlobeHost />, {
      route: "/home",
      authValue: authedValue("user-1"),
      queryClient,
    });
    const homeAltitude = (await screen.findByTestId("globe-canvas")).getAttribute("data-pov-altitude");
    home.unmount();

    renderJourneyAdd({ route: null, queryClient });
    const globe = await screen.findByTestId("globe-canvas");

    await waitFor(() => expect(globe).toHaveAttribute("data-route", "none"));
    expect(globe).toHaveAttribute("data-pov-altitude", homeAltitude);
  });

  it("уход на дашборд: маршрут остаётся и гаснет во время перелёта, затем снимается", async () => {
    const { container, user } = renderJourneyAdd();
    const globe = await screen.findByTestId("globe-canvas");
    await waitFor(() => expect(globe).toHaveAttribute("data-route", "Moscow"));

    await user.click(screen.getByRole("button", { name: "go /home" }));

    expect(screenAttr(container, "data-screen")).toBe("home");
    expect(globe).toHaveAttribute("data-route", "Moscow");
    expect(globe).toHaveAttribute("data-route-fading", "true");
    // The form face framing leaves with it: the frame flies to the dashboard.
    expect(container.querySelector<HTMLElement>(".persistent-globe")?.style.getPropertyValue("--globe-slot-clip")).toBe(
      "",
    );
    await waitFor(() => expect(globe).toHaveAttribute("data-route", "none"), { timeout: 2000 });
    expect(globe).toHaveAttribute("data-route-fading", "false");
  });

  it.each([
    { path: "/journeys", reason: "2D-карта: оболочку сразу закрашивает своя ночь" },
    { path: "/login", reason: "выход из аккаунта: маршрут лёг бы поверх курируемых дуг" },
  ])("уход на $path маршрут не удерживает — $reason", async ({ path }) => {
    const { user } = renderJourneyAdd();
    const globe = await screen.findByTestId("globe-canvas");
    await waitFor(() => expect(globe).toHaveAttribute("data-route", "Moscow"));

    await user.click(screen.getByRole("button", { name: `go ${path}` }));

    expect(globe).toHaveAttribute("data-route", "none");
    expect(globe).toHaveAttribute("data-route-fading", "false");
  });

  it("при prefers-reduced-motion маршрут на уходе не удерживается — снимается сразу", async () => {
    vi.stubGlobal("matchMedia", (query: string) => ({
      matches: true,
      media: query,
      addEventListener: () => {},
      removeEventListener: () => {},
    }));
    const { user } = renderJourneyAdd();
    const globe = await screen.findByTestId("globe-canvas");
    await waitFor(() => expect(globe).toHaveAttribute("data-route", "Moscow"));

    await user.click(screen.getByRole("button", { name: "go /home" }));

    expect(globe).toHaveAttribute("data-route", "none");
  });
});

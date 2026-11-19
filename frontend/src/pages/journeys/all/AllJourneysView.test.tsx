import { fireEvent } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { FEED_JOURNEYS, server } from "../../../test/handlers";
import { intersectAllObserved, reportIntersection } from "../../../test/intersection";
import { stubScreenLayout } from "../../../test/layout";
import { matchMediaQueries } from "../../../test/motion";
import { renderAllJourneys } from "../../../test/journeysMap";
import { act, screen, waitFor, within } from "../../../test/render";

const DESKTOP_QUERY = "(min-width: 62em)";

/** Replaces the feed and records each request's query, so the test sees which filters went out. */
function recordFeedRequests(
  respond: (params: URLSearchParams) => Response | Promise<Response> = () =>
    HttpResponse.json({ items: FEED_JOURNEYS, nextCursor: null }),
) {
  const requests: URLSearchParams[] = [];
  server.use(
    http.get("/v1/journeys/", ({ request }) => {
      const params = new URL(request.url).searchParams;
      requests.push(params);
      return respond(params);
    }),
  );
  return requests;
}

describe("AllJourneysView", () => {
  it("показывает поездки по годам — свежий год сверху — с названиями мест и расстоянием", async () => {
    renderAllJourneys();

    const year2021 = await screen.findByRole("region", { name: "2021" });
    const year2019 = screen.getByRole("region", { name: "2019" });
    expect(year2021.compareDocumentPosition(year2019) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(await within(year2021).findByRole("link", { name: "Air Moscow to London 2,500 km" })).toBeInTheDocument();
    expect(within(year2021).getAllByRole("listitem")).toHaveLength(2);
    expect(within(year2021).getByText("2,500 km")).toBeInTheDocument();
    expect(within(year2019).getAllByRole("listitem")).toHaveLength(1);
  });

  it("наведённая поездка — дуга на карте с названиями её мест; другая строка меняет подписи", async () => {
    matchMediaQueries(DESKTOP_QUERY);
    const { container } = renderAllJourneys();
    const year2021 = await screen.findByRole("region", { name: "2021" });
    await within(year2021).findByRole("link", { name: /Moscow to London/u });
    const [moscowToLondon, londonToParis] = within(year2021).getAllByRole("listitem");
    const mapLabels = () => [...container.querySelectorAll(".feed-arc__label")].map((label) => label.textContent).sort();

    fireEvent.pointerOver(moscowToLondon);
    await waitFor(() => expect(mapLabels()).toEqual(["London", "Moscow"]));

    fireEvent.pointerOver(londonToParis);
    await waitFor(() => expect(mapLabels()).toEqual(["London", "Paris"]));
  });

  it("дуга наведённой поездки кончается стрелкой у места назначения", async () => {
    matchMediaQueries(DESKTOP_QUERY);
    const { container } = renderAllJourneys();
    const year2021 = await screen.findByRole("region", { name: "2021" });
    await within(year2021).findByRole("link", { name: /Moscow to London/u });
    const [moscowToLondon] = within(year2021).getAllByRole("listitem");

    fireEvent.pointerOver(moscowToLondon);

    await waitFor(() => expect(container.querySelectorAll(".feed-arc__line")).toHaveLength(1));
    const [line] = container.querySelectorAll(".feed-arc__line");
    expect(line.getAttribute("marker-end")).toBe("url(#feed-arc-arrow)");
    expect(container.querySelector("#feed-arc-arrow")).not.toBeNull();
  });

  it("дуга через край мира: стрелка только на куске, который приходит в место назначения", async () => {
    matchMediaQueries(DESKTOP_QUERY);
    // Tokyo -> Los Angeles: the shortest path crosses the Pacific, over the 180th meridian.
    const [moscowToLondon] = FEED_JOURNEYS;
    const tokyoToLosAngeles = {
      ...moscowToLondon,
      origin: { ...moscowToLondon.origin, latitude: 35.69, longitude: 139.69 },
      destination: { ...moscowToLondon.destination, latitude: 34.05, longitude: -118.24 },
    };
    recordFeedRequests(() => HttpResponse.json({ items: [tokyoToLosAngeles], nextCursor: null }));
    const { container } = renderAllJourneys();
    const year2021 = await screen.findByRole("region", { name: "2021" });
    const [row] = await within(year2021).findAllByRole("listitem");

    fireEvent.pointerOver(row);

    await waitFor(() => expect(container.querySelectorAll(".feed-arc__line")).toHaveLength(2));
    const lines = [...container.querySelectorAll(".feed-arc__line")];
    expect(lines.map((line) => line.getAttribute("marker-end"))).toEqual([null, "url(#feed-arc-arrow)"]);
  });

  it("на узком экране карты за лентой нет", async () => {
    const { container } = renderAllJourneys();
    await screen.findByRole("region", { name: "2021" });
    // The shared map is a lazy chunk: let it resolve, so its absence is not just a pending load.
    await act(async () => {
      await import("../map/JourneysSharedMap");
    });

    expect(container.querySelector(".world-map")).toBeNull();
  });

  it("кадр карты переезжает к наведённой поездке и остаётся на ней, когда курсор ушёл с ленты", async () => {
    matchMediaQueries(DESKTOP_QUERY, "prefers-reduced-motion");
    stubScreenLayout({
      "world-map": { left: 0, top: 0, width: 1000, height: 487 },
      "world-map-canvas": { left: 0, top: 0, width: 1000, height: 487 },
      "world-map-wrap": { left: 0, top: 0, width: 1000, height: 487 },
      "all-journeys__column": { left: 0, top: 0, width: 400, height: 487 },
    });
    const { container } = renderAllJourneys();
    const year2021 = await screen.findByRole("region", { name: "2021" });
    const [moscowToLondon, londonToParis] = within(year2021).getAllByRole("listitem");
    const viewBox = () => container.querySelector(".world-map")?.getAttribute("viewBox");
    await waitFor(() => expect(viewBox()).toBeTruthy());
    const allJourneysFrame = viewBox();

    // London -> Paris is short and apart from the others: its frame differs from the all-journeys frame.
    fireEvent.pointerOver(londonToParis);
    await waitFor(() => expect(viewBox()).not.toBe(allJourneysFrame));
    const londonToParisFrame = viewBox();
    fireEvent.pointerOver(moscowToLondon);
    await waitFor(() => expect(viewBox()).not.toBe(londonToParisFrame));
    fireEvent.pointerOver(londonToParis);
    await waitFor(() => expect(viewBox()).toBe(londonToParisFrame));
    fireEvent.pointerLeave(container.querySelector(".journey-feed") ?? container);

    // The arc left with the cursor but the frame did not: it does not return to the all-journeys frame.
    await waitFor(() => expect(container.querySelector(".feed-arc")).toBeNull());
    expect(viewBox()).toBe(londonToParisFrame);
  });

  it("без поездок предлагает добавить первую", async () => {
    server.use(
      http.get("/v1/journeys/", () => HttpResponse.json({ items: [], nextCursor: null })),
      http.get("/v1/journeys/years/", () => HttpResponse.json({ years: [] })),
    );
    renderAllJourneys();

    expect(await screen.findByText("No journeys yet")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Add your first journey" })).toHaveAttribute("href", "/journeys/add");
  });

  it("ползунок лет сужает ленту, запрос уходит, когда ручка остановилась; ручки по краям — все годы", async () => {
    const requests = recordFeedRequests();
    const { user } = renderAllJourneys();
    await screen.findByRole("region", { name: "2021" });

    screen.getByRole("slider", { name: "To year" }).focus();
    await user.keyboard("{ArrowLeft}{ArrowLeft}");

    await waitFor(() => expect(requests.at(-1)?.toString()).toBe("yearFrom=2019&yearTo=2019"));
    // The intermediate window 2019-2020 was cancelled before the network: the thumb moved in a row, one request.
    expect(requests.map((params) => params.toString())).toEqual(["", "yearFrom=2019&yearTo=2019"]);

    await user.keyboard("{ArrowRight}{ArrowRight}");

    // Thumbs at the edges again means no filter: the same key as the first request, the feed from cache.
    expect(await screen.findByRole("region", { name: "2021" })).toBeInTheDocument();
    expect(requests).toHaveLength(2);
  });

  it("лента загружена целиком — новый фильтр виден сразу, до ответа сервера, и не приглушён", async () => {
    // Hold the filtered response: everything on screen before it is built on the client.
    let releaseFiltered = () => {};
    const filteredGate = new Promise<void>((resolve) => {
      releaseFiltered = resolve;
    });
    recordFeedRequests((params) =>
      params.has("yearFrom")
        ? filteredGate.then(() => HttpResponse.json({ items: [FEED_JOURNEYS[2]], nextCursor: null }))
        : HttpResponse.json({ items: FEED_JOURNEYS, nextCursor: null }),
    );
    const { user, container } = renderAllJourneys();
    await screen.findByRole("region", { name: "2021" });

    screen.getByRole("slider", { name: "To year" }).focus();
    await user.keyboard("{ArrowLeft}{ArrowLeft}");

    await waitFor(() => expect(screen.queryByRole("region", { name: "2021" })).not.toBeInTheDocument());
    expect(within(screen.getByRole("region", { name: "2019" })).getAllByRole("listitem")).toHaveLength(1);
    expect(container.querySelector(".journey-feed--stale")).toBeNull();
    releaseFiltered();
  });

  it("лента загружена не вся — выборка с клиента приглушена, пока сервер не ответил", async () => {
    let releaseFiltered = () => {};
    const filteredGate = new Promise<void>((resolve) => {
      releaseFiltered = resolve;
    });
    recordFeedRequests((params) =>
      params.has("yearFrom")
        ? filteredGate.then(() => HttpResponse.json({ items: [FEED_JOURNEYS[2]], nextCursor: null }))
        : HttpResponse.json({ items: FEED_JOURNEYS, nextCursor: "page-2" }),
    );
    const { user, container } = renderAllJourneys();
    await screen.findByRole("region", { name: "2021" });

    screen.getByRole("slider", { name: "To year" }).focus();
    await user.keyboard("{ArrowLeft}{ArrowLeft}");

    await waitFor(() => expect(screen.queryByRole("region", { name: "2021" })).not.toBeInTheDocument());
    expect(container.querySelector(".journey-feed--stale")).not.toBeNull();

    releaseFiltered();
    await waitFor(() => expect(container.querySelector(".journey-feed--stale")).toBeNull());
  });

  it("заголовок года получает фон, только пока прилип к верху ленты", async () => {
    renderAllJourneys();
    const header = await screen.findByRole("heading", { name: "2021" });
    const rootBounds = DOMRect.fromRect({ x: 0, y: 100, width: 600, height: 400 });
    expect(header).not.toHaveAttribute("data-stuck");

    // Stuck: one pixel above the scroll edge and not fully visible.
    act(() =>
      reportIntersection(header, {
        intersectionRatio: 0.98,
        rootBounds,
        boundingClientRect: DOMRect.fromRect({ x: 0, y: 99, width: 600, height: 46 }),
      }),
    );
    expect(header).toHaveAttribute("data-stuck");

    // Fully visible: in its place in the feed.
    act(() =>
      reportIntersection(header, {
        intersectionRatio: 1,
        rootBounds,
        boundingClientRect: DOMRect.fromRect({ x: 0, y: 220, width: 600, height: 46 }),
      }),
    );
    expect(header).not.toHaveAttribute("data-stuck");

    // Cut off at the bottom, at the lower scroll edge: that is not sticking.
    act(() =>
      reportIntersection(header, {
        intersectionRatio: 0.5,
        rootBounds,
        boundingClientRect: DOMRect.fromRect({ x: 0, y: 477, width: 600, height: 46 }),
      }),
    );
    expect(header).not.toHaveAttribute("data-stuck");
  });

  it("поездки только за один год — шкалы лет нет, выбирать не из чего", async () => {
    server.use(http.get("/v1/journeys/years/", () => HttpResponse.json({ years: [2021] })));
    renderAllJourneys();

    await screen.findByRole("region", { name: "2021" });

    expect(screen.queryByRole("slider")).not.toBeInTheDocument();
    expect(screen.queryByRole("group", { name: "Years" })).not.toBeInTheDocument();
  });

  it("снятый вид транспорта уходит фильтром из оставшихся; без транспорта лента не запрашивается", async () => {
    const requests = recordFeedRequests();
    const { user } = renderAllJourneys();
    await screen.findByRole("region", { name: "2021" });

    await user.click(screen.getByRole("checkbox", { name: "Air" }));
    await waitFor(() => expect(requests.at(-1)?.getAll("transportType")).toEqual(["land", "water"]));

    await user.click(screen.getByRole("checkbox", { name: "Land" }));
    await user.click(screen.getByRole("checkbox", { name: "Water" }));
    const requestCount = requests.length;

    expect(await screen.findByText("Choose at least one transport")).toBeInTheDocument();
    expect(requests).toHaveLength(requestCount);
  });

  it("фильтр без совпадений — отдельное сообщение, а не «поездок пока нет»", async () => {
    recordFeedRequests((params) =>
      HttpResponse.json({ items: params.has("yearFrom") ? [] : FEED_JOURNEYS, nextCursor: null }),
    );
    const { user } = renderAllJourneys();

    (await screen.findByRole("slider", { name: "To year" })).focus();
    await user.keyboard("{ArrowLeft}");

    expect(await screen.findByText("No journeys match these filters")).toBeInTheDocument();
    expect(screen.queryByText("No journeys yet")).not.toBeInTheDocument();
  });

  it("сторож в конце ленты догружает следующую порцию по курсору; строка из двух порций — одна", async () => {
    const londonToMoscow = {
      ...FEED_JOURNEYS[0],
      journeyId: "aaaaaaaa-0000-4000-8000-000000000004",
      origin: FEED_JOURNEYS[0].destination,
      destination: FEED_JOURNEYS[0].origin,
      traveledYear: 2018,
    };
    const requests = recordFeedRequests((params) =>
      params.get("cursor") === "page-2"
        ? HttpResponse.json({ items: [FEED_JOURNEYS[2], londonToMoscow], nextCursor: null })
        : HttpResponse.json({ items: FEED_JOURNEYS, nextCursor: "page-2" }),
    );
    renderAllJourneys();
    await screen.findByRole("region", { name: "2019" });

    act(() => intersectAllObserved());

    const year2018 = await screen.findByRole("region", { name: "2018" });
    expect(within(year2018).getAllByRole("listitem")).toHaveLength(1);
    expect(within(screen.getByRole("region", { name: "2019" })).getAllByRole("listitem")).toHaveLength(1);
    expect(requests.map((params) => params.get("cursor"))).toEqual([null, "page-2"]);
  });

  it("порция не догрузилась — сообщение у конца ленты и повтор, который её догружает", async () => {
    let isFailing = true;
    recordFeedRequests((params) => {
      if (params.get("cursor") !== "page-2") {
        return HttpResponse.json({ items: FEED_JOURNEYS.slice(0, 2), nextCursor: "page-2" });
      }

      return isFailing
        ? HttpResponse.json({ code: "internal_error", message: "boom" }, { status: 500 })
        : HttpResponse.json({ items: FEED_JOURNEYS.slice(2), nextCursor: null });
    });
    const { user } = renderAllJourneys();
    await screen.findByRole("region", { name: "2021" });

    act(() => intersectAllObserved());

    expect(await screen.findByText("Couldn't load more journeys")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "2021" })).toBeInTheDocument();
    isFailing = false;
    await user.click(screen.getByRole("button", { name: "Try again" }));

    expect(await screen.findByRole("region", { name: "2019" })).toBeInTheDocument();
    expect(screen.queryByText("Couldn't load more journeys")).not.toBeInTheDocument();
  });

  it("ошибка загрузки ленты — сообщение и повтор, который её показывает", async () => {
    let isFailing = true;
    recordFeedRequests(() =>
      isFailing
        ? HttpResponse.json({ code: "internal_error", message: "boom" }, { status: 500 })
        : HttpResponse.json({ items: FEED_JOURNEYS, nextCursor: null }),
    );
    const { user } = renderAllJourneys();

    expect(await screen.findByText("Couldn't load your journeys")).toBeInTheDocument();
    isFailing = false;
    await user.click(screen.getByRole("button", { name: "Try again" }));

    expect(await screen.findByRole("region", { name: "2021" })).toBeInTheDocument();
  });
});

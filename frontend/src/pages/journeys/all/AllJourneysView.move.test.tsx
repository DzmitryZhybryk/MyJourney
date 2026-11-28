import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { FEED_JOURNEYS, server } from "../../../test/handlers";
import { renderAllJourneys } from "../../../test/journeysMap";
import { screen, waitFor, within } from "../../../test/render";

const [FIRST_2021, LONDON_TO_PARIS, PARIS_TO_MOSCOW] = FEED_JOURNEYS;
const ROW_HEIGHT = 44;
const ROW_STEP = 50;

/**
 * Stacks the feed rows in a column in DOM order: in jsdom all rectangles are zero and dnd-kit
 * could not tell which row is lower. Other elements stay zero.
 */
function stackRowsVertically() {
  vi.spyOn(Element.prototype, "getBoundingClientRect").mockImplementation(function rectOf(this: Element) {
    const index = [...document.querySelectorAll("[data-flip-id]")].indexOf(this);
    return index === -1
      ? DOMRect.fromRect({ x: 0, y: 0, width: 0, height: 0 })
      : DOMRect.fromRect({ x: 0, y: index * ROW_STEP, width: 600, height: ROW_HEIGHT });
  });
  vi.spyOn(HTMLElement.prototype, "offsetTop", "get").mockImplementation(function topOf(this: HTMLElement) {
    return Math.max([...document.querySelectorAll("[data-flip-id]")].indexOf(this), 0) * ROW_STEP;
  });
}

/** Drags the London -> Paris (2021) row one row down with the keyboard: space, arrow, space. */
async function dragLondonToParisDown(user: ReturnType<typeof renderAllJourneys>["user"]) {
  const year2021 = await screen.findByRole("region", { name: "2021" });
  const handles = within(year2021).getAllByRole("button", { name: "Drag to reorder" });
  handles[1].focus();
  await user.keyboard(" ");
  await user.keyboard("{ArrowDown}");
  await user.keyboard(" ");
}

describe("AllJourneysView — перенос", () => {
  it("строка, перенесённая с клавиатуры в другой год, встаёт туда до ответа, а на сервер уходит сосед и сторона", async () => {
    stackRowsVertically();
    let request: { url: string; body: unknown } | null = null;
    // Hold the move response while the test looks at the feed: the reorder must be visible before it.
    let releaseResponse = () => {};
    const responseGate = new Promise<void>((resolve) => {
      releaseResponse = resolve;
    });
    server.use(
      http.post("/v1/journeys/:journeyId/move/", async ({ request: incoming }) => {
        request = { url: new URL(incoming.url).pathname, body: await incoming.json() };
        await responseGate;
        return HttpResponse.json({ traveledYear: 2019 });
      }),
    );
    const { user } = renderAllJourneys();

    await dragLondonToParisDown(user);

    await waitFor(() =>
      expect(request).toEqual({
        url: `/v1/journeys/${LONDON_TO_PARIS.journeyId}/move/`,
        body: { neighborJourneyId: PARIS_TO_MOSCOW.journeyId, placement: "after" },
      }),
    );
    expect(within(screen.getByRole("region", { name: "2019" })).getAllByRole("listitem")).toHaveLength(2);
    expect(within(screen.getByRole("region", { name: "2021" })).getAllByRole("listitem")).toHaveLength(1);
    releaseResponse();
    // Finish the move here: its late requests would otherwise leak into the next test's mocks.
    await waitFor(() =>
      expect(screen.getAllByRole("button", { name: "Drag to reorder" }).every((handle) => !handle.hasAttribute("disabled"))).toBe(true),
    );
  });

  it("брошенная строка остаётся там, где её отпустили, без повтора анимации; показанная лента не перезапрашивается", async () => {
    stackRowsVertically();
    // jsdom has no Web Animations: a spy on the prototype; without it FLIP silently skips the animation.
    const animate = vi.fn();
    Object.defineProperty(HTMLElement.prototype, "animate", { configurable: true, writable: true, value: animate });
    let feedRequests = 0;
    let yearsRequests = 0;
    server.use(
      http.get("/v1/journeys/", () => {
        feedRequests += 1;
        return HttpResponse.json({ items: FEED_JOURNEYS, nextCursor: null });
      }),
      http.get("/v1/journeys/years/", () => {
        yearsRequests += 1;
        return HttpResponse.json({ years: [2019, 2021] });
      }),
      http.post("/v1/journeys/:journeyId/move/", () => HttpResponse.json({ traveledYear: 2019 })),
    );
    try {
      const { user } = renderAllJourneys();

      await dragLondonToParisDown(user);

      // The year changed, so years are refetched; the feed is invalidated in the same step, right after them.
      await waitFor(() => expect(yearsRequests).toBe(2));
      expect(within(screen.getByRole("region", { name: "2019" })).getAllByRole("listitem")).toHaveLength(2);
      expect(within(screen.getByRole("region", { name: "2021" })).getAllByRole("listitem")).toHaveLength(1);
      expect(feedRequests).toBe(1);
      expect(animate).not.toHaveBeenCalled();
    } finally {
      Reflect.deleteProperty(HTMLElement.prototype, "animate");
    }
  });

  it("бэк отказал в переносе — строка возвращается на место сама, не дожидаясь перезапроса ленты", async () => {
    stackRowsVertically();
    // Hold the feed refetch after the refusal: the rollback, not the refetch, must put the row back.
    let feedRequests = 0;
    let releaseRefetch = () => {};
    const refetchGate = new Promise<void>((resolve) => {
      releaseRefetch = resolve;
    });
    server.use(
      http.get("/v1/journeys/", async () => {
        feedRequests += 1;
        if (feedRequests === 1) {
          return HttpResponse.json({ items: FEED_JOURNEYS, nextCursor: null });
        }

        // The refetch returns a feed changed on the server meanwhile: the 2019 neighbour is gone.
        await refetchGate;
        return HttpResponse.json({ items: [FIRST_2021, LONDON_TO_PARIS], nextCursor: null });
      }),
      http.post("/v1/journeys/:journeyId/move/", () =>
        HttpResponse.json({ code: "journeys.invalid_move_target", message: "нет" }, { status: 400 }),
      ),
    );
    const { user } = renderAllJourneys();

    await dragLondonToParisDown(user);

    expect(await screen.findByText("Couldn't move the journey there. The list has been refreshed")).toBeInTheDocument();
    await waitFor(() => expect(feedRequests).toBe(2));
    expect(within(screen.getByRole("region", { name: "2021" })).getAllByRole("listitem")).toHaveLength(2);
    expect(within(screen.getByRole("region", { name: "2019" })).getAllByRole("listitem")).toHaveLength(1);

    releaseRefetch();
    // The feed arrives from the server; wait for it so the request is not aborted by unmounting after the test.
    await waitFor(() => expect(screen.queryByRole("region", { name: "2019" })).not.toBeInTheDocument());
  });

  it("пока строку несут в другой год, вместо расстояния у неё подсказка «→ год»", async () => {
    stackRowsVertically();
    const { user } = renderAllJourneys();
    const year2021 = await screen.findByRole("region", { name: "2021" });
    within(year2021).getAllByRole("button", { name: "Drag to reorder" })[1].focus();

    await user.keyboard(" ");
    expect(screen.queryByText("→ 2019")).not.toBeInTheDocument();
    await user.keyboard("{ArrowDown}");

    expect(await screen.findByText("→ 2019")).toBeInTheDocument();
    expect(screen.queryByText("344 km")).not.toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(screen.getByText("344 km")).toBeInTheDocument();
  });

  it("пока строку несут в другой год, заголовок этого года уступает ей место, а после отмены возвращается", async () => {
    stackRowsVertically();
    const { user } = renderAllJourneys();
    const year2021 = await screen.findByRole("region", { name: "2021" });
    within(year2021).getAllByRole("button", { name: "Drag to reorder" })[1].focus();
    const header2019 = screen.getByRole("heading", { name: "2019" });

    await user.keyboard(" ");
    await user.keyboard("{ArrowDown}");
    // Finish the move whatever the outcome: an unfinished one would leak into the next test.
    try {
      await waitFor(() => expect(header2019.style.transform).toBe(`translateY(-${ROW_HEIGHT}px)`));
      expect(screen.getByRole("heading", { name: "2021" }).style.transform).toBe("");
    } finally {
      await user.keyboard("{Escape}");
    }

    expect(header2019.style.transform).toBe("");
  });

  it("Esc во время переноса отменяет его без запроса", async () => {
    stackRowsVertically();
    const moveSpy = vi.fn();
    server.use(
      http.post("/v1/journeys/:journeyId/move/", () => {
        moveSpy();
        return HttpResponse.json({ traveledYear: 2019 });
      }),
    );
    const { user } = renderAllJourneys();
    const year2021 = await screen.findByRole("region", { name: "2021" });
    within(year2021).getAllByRole("button", { name: "Drag to reorder" })[1].focus();

    await user.keyboard(" ");
    await user.keyboard("{ArrowDown}");
    await user.keyboard("{Escape}");

    expect(within(screen.getByRole("region", { name: "2021" })).getAllByRole("listitem")).toHaveLength(2);
    expect(moveSpy).not.toHaveBeenCalled();
  });
});

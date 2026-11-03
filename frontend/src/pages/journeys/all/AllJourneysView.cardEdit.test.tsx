import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import type { JourneyFeedEntry } from "../../../api/sdk";
import { pickCity } from "../../../test/addJourney";
import { FEED_JOURNEYS, GEO_CITIES, server } from "../../../test/handlers";
import { openMoscowToLondonCard, renderAllJourneys, serveFeedByYears } from "../../../test/journeysMap";
import { findMenuItem, screen, waitFor, within } from "../../../test/render";

const [MOSCOW, LONDON, PARIS] = GEO_CITIES;
const [MOSCOW_TO_LONDON] = FEED_JOURNEYS;

/** Records the bodies of journey saves (PUT) and answers 204, as the backend does. */
function recordSaves(): unknown[] {
  const bodies: unknown[] = [];
  server.use(
    http.put("/v1/journeys/:journeyId/", async ({ request }) => {
      bodies.push(await request.json());
      return new HttpResponse(null, { status: 204 });
    }),
  );
  return bodies;
}

/** The whole Moscow -> London journey as a save sends it, with the changed fields. */
function savedMoscowToLondon(changes: Record<string, unknown>): Record<string, unknown> {
  return {
    originCityId: MOSCOW.cityId,
    destinationCityId: LONDON.cityId,
    transportType: "air",
    traveledYear: 2021,
    ...changes,
  };
}

/** The card: a region named by its route title ("Moscow to London"). */
function card(): HTMLElement {
  return screen.getByRole("region", { name: / to /u });
}

describe("AllJourneysView — правка в карточке поездки", () => {
  it("транспорт из меню сохраняется сразу: PUT со всей поездкой и «Saved · Undo»", async () => {
    const saves = recordSaves();
    const { user } = await openMoscowToLondonCard();

    await user.click(within(card()).getByRole("button", { name: "Air" }));
    await user.click(await findMenuItem("Water"));

    await waitFor(() => expect(saves).toEqual([savedMoscowToLondon({ transportType: "water" })]));
    expect(await screen.findByText("Saved")).toBeInTheDocument();
    expect(within(card()).getByRole("button", { name: "Water" })).toBeInTheDocument();
  });

  it("«Undo» сохраняет прежние значения и больше не предлагает отмену", async () => {
    const saves = recordSaves();
    const { user } = await openMoscowToLondonCard();
    await user.click(within(card()).getByRole("button", { name: "Air" }));
    await user.click(await findMenuItem("Water"));

    await user.click(await screen.findByRole("button", { name: "Undo" }));

    await waitFor(() =>
      expect(saves).toEqual([savedMoscowToLondon({ transportType: "water" }), savedMoscowToLondon({ transportType: "air" })]),
    );
    expect(await screen.findByText("Change undone")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Undo" })).not.toBeInTheDocument();
    expect(within(card()).getByRole("button", { name: "Air" })).toBeInTheDocument();
  });

  it("«Undo» с клавиатуры: кнопка уходит вместе со статусом, фокус — на заголовок карточки", async () => {
    const { user } = await openMoscowToLondonCard();
    await user.click(within(card()).getByRole("button", { name: "Air" }));
    await user.click(await findMenuItem("Water"));

    (await screen.findByRole("button", { name: "Undo" })).focus();
    await user.keyboard("{Enter}");

    expect(await screen.findByText("Change undone")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("heading", { level: 1, name: "Moscow to London" })).toHaveFocus());
  });

  it("пока сохранение идёт, значения не правятся, но фокус не теряют: они aria-disabled, а не disabled", async () => {
    let respond!: () => void;
    const responded = new Promise<void>((resolve) => {
      respond = resolve;
    });
    server.use(
      http.put("/v1/journeys/:journeyId/", async () => {
        await responded;
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const { user } = await openMoscowToLondonCard();

    await user.click(within(card()).getByRole("button", { name: "Air" }));
    await user.click(await findMenuItem("Water"));

    // A disabled button drops its focus to the body, and the value just picked holds the focus.
    const transport = within(card()).getByRole("button", { name: "Water" });
    const year = within(card()).getByRole("button", { name: "2021" });
    const swap = screen.getByRole("button", { name: "Swap origin and destination" });
    await waitFor(() => expect(transport).toHaveAttribute("aria-disabled", "true"));
    expect(year).toHaveAttribute("aria-disabled", "true");
    expect(swap).toHaveAttribute("aria-disabled", "true");
    expect(transport).toBeEnabled();
    expect(year).toBeEnabled();
    expect(swap).toBeEnabled();

    await user.click(year);
    expect(screen.queryByRole("option", { name: "2019", hidden: true })).not.toBeInTheDocument();
    respond();
    await waitFor(() => expect(transport).toHaveAttribute("aria-disabled", "false"));
  });

  it("выбор того же значения не отправляет запрос и не пишет «Saved»", async () => {
    const saves = recordSaves();
    const { user } = await openMoscowToLondonCard();

    await user.click(within(card()).getByRole("button", { name: "Air" }));
    await user.click(await findMenuItem("Air"));

    await waitFor(() => expect(screen.queryByRole("menu")).not.toBeInTheDocument());
    expect(saves).toEqual([]);
    expect(screen.queryByText("Saved")).not.toBeInTheDocument();
  });

  it("город: клик открывает поле с подсказками, выбор сохраняет маршрут, расстояние новой пары — оценка сервера", async () => {
    const saves = recordSaves();
    const { user } = await openMoscowToLondonCard();

    await user.click(within(card()).getByRole("button", { name: "London" }));
    expect(screen.getByLabelText("To")).toHaveFocus();
    await user.clear(screen.getByLabelText("To"));
    await pickCity({ user, label: "To", query: "Par", option: /Paris/iu });

    await waitFor(() => expect(saves).toEqual([savedMoscowToLondon({ destinationCityId: PARIS.cityId })]));
    expect(await screen.findByRole("heading", { level: 1, name: "Moscow to Paris" })).toBeInTheDocument();
    expect(await within(card()).findByText("1,234 km")).toBeInTheDocument();
  });

  it("пока правится город, карточка остаётся регионом с именем маршрута", async () => {
    const { user } = await openMoscowToLondonCard();

    await user.click(within(card()).getByRole("button", { name: "London" }));

    expect(card()).toContainElement(screen.getByLabelText("To"));
  });

  it("тот же город в обоих концах — ошибка под маршрутом, запроса нет, маршрут прежний", async () => {
    const saves = recordSaves();
    const { user } = await openMoscowToLondonCard();

    await user.click(within(card()).getByRole("button", { name: "London" }));
    await user.clear(screen.getByLabelText("To"));
    await pickCity({ user, label: "To", query: "Mos", option: /Moscow/iu });

    expect(await screen.findByText("Departure and destination must differ")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "Moscow to London" })).toBeInTheDocument();
    expect(saves).toEqual([]);
  });

  it("Esc без подсказок закрывает поле города с первого раза, без запроса, фокус — на город", async () => {
    const saves = recordSaves();
    const { user } = await openMoscowToLondonCard();
    await user.click(within(card()).getByRole("button", { name: "London" }));

    await user.keyboard("{Escape}");

    expect(screen.queryByLabelText("To")).not.toBeInTheDocument();
    expect(within(card()).getByRole("button", { name: "London" })).toHaveFocus();
    expect(saves).toEqual([]);
  });

  it("Esc при показанных подсказках закрывает только их, второй Esc — поле", async () => {
    const { user } = await openMoscowToLondonCard();
    await user.click(within(card()).getByRole("button", { name: "London" }));
    const to = screen.getByLabelText("To");
    await user.clear(to);
    await user.type(to, "Par");
    await waitFor(() => {
      const listId = to.getAttribute("aria-controls");
      expect(listId && document.getElementById(listId)?.querySelector('[role="option"]')).toBeTruthy();
    });

    await user.keyboard("{Escape}");
    expect(screen.getByLabelText("To")).toBeInTheDocument();

    await user.keyboard("{Escape}");
    expect(screen.queryByLabelText("To")).not.toBeInTheDocument();
  });

  it("смена направления — одно сохранение с городами наоборот", async () => {
    const saves = recordSaves();
    const { user } = await openMoscowToLondonCard();

    await user.click(screen.getByRole("button", { name: "Swap origin and destination" }));

    await waitFor(() =>
      expect(saves).toEqual([savedMoscowToLondon({ originCityId: LONDON.cityId, destinationCityId: MOSCOW.cityId })]),
    );
    expect(await screen.findByRole("heading", { level: 1, name: "London to Moscow" })).toBeInTheDocument();
  });

  it("год: клик открывает список лет, выбор сохраняется сразу", async () => {
    const saves = recordSaves();
    const { user } = await openMoscowToLondonCard();

    await user.click(within(card()).getByRole("button", { name: "2021" }));
    await user.click(await screen.findByRole("option", { name: "2019", hidden: true }));

    await waitFor(() => expect(saves).toEqual([savedMoscowToLondon({ traveledYear: 2019 })]));
    expect(await within(card()).findByRole("button", { name: "2019" })).toBeInTheDocument();
  });

  it("поездка ушла из выбранных лет после смены года — карточка остаётся открытой", async () => {
    let journeys: readonly JourneyFeedEntry[] = FEED_JOURNEYS;
    serveFeedByYears(() => journeys);
    server.use(
      http.put("/v1/journeys/:journeyId/", async ({ request }) => {
        const { traveledYear } = (await request.json()) as { traveledYear: number };
        journeys = journeys.map((journey) =>
          journey.journeyId === MOSCOW_TO_LONDON.journeyId ? { ...journey, traveledYear } : journey,
        );
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const { user } = renderAllJourneys();
    await screen.findByRole("region", { name: "2019" });
    screen.getByRole("slider", { name: "From year" }).focus();
    await user.keyboard("{ArrowRight}{ArrowRight}");
    await waitFor(() => expect(screen.queryByRole("region", { name: "2019" })).not.toBeInTheDocument());
    await user.click(await screen.findByRole("link", { name: /Moscow to London/u }));
    await screen.findByRole("heading", { level: 1, name: "Moscow to London" });

    await user.click(within(card()).getByRole("button", { name: "2021" }));
    await user.click(await screen.findByRole("option", { name: "2019", hidden: true }));

    // The hidden feed refetched without the journey: its year left the selected years.
    await waitFor(() =>
      expect(screen.queryByRole("link", { name: /Moscow to London/u, hidden: true })).not.toBeInTheDocument(),
    );
    expect(screen.getByRole("heading", { level: 1, name: "Moscow to London" })).toBeInTheDocument();
    expect(within(card()).getByRole("button", { name: "2019" })).toBeInTheDocument();
  });

  it("поездку удалили в другом месте — сохранение говорит об этом, значение прежнее", async () => {
    server.use(
      http.put("/v1/journeys/:journeyId/", () =>
        HttpResponse.json({ code: "journeys.journey_not_found", message: "нет" }, { status: 404 }),
      ),
    );
    const { user } = await openMoscowToLondonCard();

    await user.click(within(card()).getByRole("button", { name: "Air" }));
    await user.click(await findMenuItem("Water"));

    expect(await screen.findByText("This journey no longer exists")).toBeInTheDocument();
    expect(within(card()).getByRole("button", { name: "Air" })).toBeInTheDocument();
    expect(screen.queryByText("Saved")).not.toBeInTheDocument();
  });

  it("город отклонён сервером — ошибка под маршрутом, маршрут прежний", async () => {
    server.use(
      http.put("/v1/journeys/:journeyId/", () =>
        HttpResponse.json(
          { code: "journeys.unknown_city", message: "нет", details: { city_ids: [PARIS.cityId] } },
          { status: 400 },
        ),
      ),
    );
    const { user } = await openMoscowToLondonCard();

    await user.click(within(card()).getByRole("button", { name: "London" }));
    await user.clear(screen.getByLabelText("To"));
    await pickCity({ user, label: "To", query: "Par", option: /Paris/iu });

    expect(await screen.findByText("This city wasn't found. Pick it from the suggestions again")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "Moscow to London" })).toBeInTheDocument();
  });

  it("своя пара поездки показывает её расстояние без запроса оценки", async () => {
    const distanceSpy = vi.fn();
    server.use(
      http.get("/v1/journeys/distance/", () => {
        distanceSpy();
        return HttpResponse.json({ distanceKm: 1 });
      }),
    );

    await openMoscowToLondonCard();

    expect(within(card()).getByText("2,500 km")).toBeInTheDocument();
    expect(distanceSpy).not.toHaveBeenCalled();
  });

  it("новая пара: пока считается — приглушённый прочерк, ошибка оценки — прочерк, а не число", async () => {
    let respond!: () => void;
    const responded = new Promise<void>((resolve) => {
      respond = resolve;
    });
    server.use(
      http.get("/v1/journeys/distance/", async () => {
        await responded;
        return HttpResponse.json({ code: "journeys.unknown_city", message: "нет", details: null }, { status: 400 });
      }),
    );
    const { user } = await openMoscowToLondonCard();

    await user.click(within(card()).getByRole("button", { name: "London" }));
    await user.clear(screen.getByLabelText("To"));
    await pickCity({ user, label: "To", query: "Par", option: /Paris/iu });

    const distance = await within(card()).findByText("—");
    expect(distance).toHaveAttribute("aria-busy", "true");
    respond();
    await waitFor(() => expect(distance).toHaveAttribute("aria-busy", "false"));
    expect(distance).toHaveTextContent("—");
  });
});

import { fireEvent } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { FEED_JOURNEYS, server } from "../../../test/handlers";
import { openMoscowToLondonCard, renderAllJourneys, serveFeedByYears } from "../../../test/journeysMap";
import { matchMediaQueries } from "../../../test/motion";
import { screen, waitFor, within } from "../../../test/render";

const DESKTOP_QUERY = "(min-width: 62em)";
const [, LONDON_TO_PARIS] = FEED_JOURNEYS;
const MISSING_JOURNEY_ID = "aaaaaaaa-0000-4000-8000-0000000000ff";

describe("AllJourneysView — карточка поездки", () => {
  it("клик по строке открывает карточку вместо ленты и фильтров: маршрут, транспорт, год, расстояние; фокус на маршруте", async () => {
    await openMoscowToLondonCard();

    const card = screen.getByRole("region", { name: "Moscow to London" });
    expect(screen.getByRole("heading", { level: 1, name: "Moscow to London" })).toHaveFocus();
    expect(within(card).getByRole("button", { name: "Air" })).toBeInTheDocument();
    expect(within(card).getByRole("button", { name: "2021" })).toBeInTheDocument();
    expect(within(card).getByText("2,500 km")).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "2021" })).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Journey filters" })).not.toBeInTheDocument();
  });

  it("в карточке заглушки фотоотчёта и впечатлений с пометкой «скоро»", async () => {
    await openMoscowToLondonCard();

    expect(screen.getByRole("heading", { level: 2, name: "Photo report Soon" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "Impressions Soon" })).toBeInTheDocument();
  });

  it("«All journeys» возвращает ленту с прежним фильтром лет, фокус — на строке закрытой поездки", async () => {
    serveFeedByYears();
    const { user } = renderAllJourneys();
    await screen.findByRole("region", { name: "2021" });
    screen.getByRole("slider", { name: "To year" }).focus();
    await user.keyboard("{ArrowLeft}{ArrowLeft}");
    await waitFor(() => expect(screen.queryByRole("region", { name: "2021" })).not.toBeInTheDocument());

    await user.click(within(screen.getByRole("region", { name: "2019" })).getByRole("link", { name: /Paris to Moscow/u }));
    await screen.findByRole("heading", { level: 1, name: "Paris to Moscow" });
    await user.click(screen.getByRole("link", { name: "All journeys" }));

    const year2019 = await screen.findByRole("region", { name: "2019" });
    expect(within(year2019).getByRole("link", { name: /Paris to Moscow/u })).toHaveFocus();
    expect(screen.queryByRole("region", { name: "2021" })).not.toBeInTheDocument();
    expect(screen.getByRole("slider", { name: "To year" })).toHaveAttribute("aria-valuenow", "2019");
  });

  it("на широком экране лента возвращается на прежнюю прокрутку, хотя скрытая её теряет", async () => {
    matchMediaQueries(DESKTOP_QUERY);
    const { user } = renderAllJourneys();
    const year2021 = await screen.findByRole("region", { name: "2021" });
    const feed = screen.getByRole("region", { name: "Journeys by year" });
    feed.scrollTop = 120;
    fireEvent.scroll(feed);

    await user.click(await within(year2021).findByRole("link", { name: /Moscow to London/u }));
    await screen.findByRole("heading", { level: 1, name: "Moscow to London" });
    // A browser drops the scroll of a box under `display: none`; jsdom keeps it, so drop it by hand.
    feed.scrollTop = 0;
    await user.click(screen.getByRole("link", { name: "All journeys" }));

    await waitFor(() => expect(feed.scrollTop).toBe(120));
  });

  it("адрес карточки поездки из загруженной ленты открывает её карточку", async () => {
    renderAllJourneys(`/journeys/all/${LONDON_TO_PARIS.journeyId}`);

    expect(await screen.findByRole("heading", { level: 1, name: "London to Paris" })).toBeInTheDocument();
  });

  it("адрес поездки, которой нет в загруженной ленте, открывает список", async () => {
    renderAllJourneys(`/journeys/all/${MISSING_JOURNEY_ID}`);

    // The filters show on the list address only: their title appearing means the address fell back.
    expect(await screen.findByRole("heading", { level: 1, name: "All journeys" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "2021" })).toBeInTheDocument();
  });

  it("лента не загрузилась по адресу карточки — ошибка и повтор, который открывает карточку, а не список", async () => {
    let feedRequests = 0;
    server.use(
      http.get("/v1/journeys/", () => {
        feedRequests += 1;
        return feedRequests === 1
          ? HttpResponse.json({ code: "internal_error", message: "boom" }, { status: 500 })
          : HttpResponse.json({ items: FEED_JOURNEYS, nextCursor: null });
      }),
    );
    const { user } = renderAllJourneys(`/journeys/all/${LONDON_TO_PARIS.journeyId}`);

    await user.click(await screen.findByRole("button", { name: "Try again" }));

    expect(await screen.findByRole("heading", { level: 1, name: "London to Paris" })).toBeInTheDocument();
  });

  it("на широком экране карта видна и показывает дугу открытой поездки", async () => {
    matchMediaQueries(DESKTOP_QUERY);
    const { container } = renderAllJourneys(`/journeys/all/${LONDON_TO_PARIS.journeyId}`);
    await screen.findByRole("heading", { level: 1, name: "London to Paris" });
    const mapLabels = () => [...container.querySelectorAll(".feed-arc__label")].map((label) => label.textContent).sort();

    await waitFor(() => expect(mapLabels()).toEqual(["London", "Paris"]));
    expect(container.querySelector(".journeys-map--hidden")).toBeNull();
  });
});

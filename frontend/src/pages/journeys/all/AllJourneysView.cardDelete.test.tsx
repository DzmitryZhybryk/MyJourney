import type { UserEvent } from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { FEED_JOURNEYS, server } from "../../../test/handlers";
import { openMoscowToLondonCard, renderAllJourneys, serveFeedByYears } from "../../../test/journeysMap";
import { findMenuItem, screen, waitFor, within } from "../../../test/render";

const [MOSCOW_TO_LONDON, , PARIS_TO_MOSCOW] = FEED_JOURNEYS;

/** Opens "⋯" -> "Delete journey" and returns the confirmation dialog. */
async function openDeleteDialog(user: UserEvent): Promise<HTMLElement> {
  await user.click(screen.getByRole("button", { name: "More actions" }));
  await user.click(await findMenuItem("Delete journey"));
  return screen.findByRole("dialog", { name: "Delete this journey?" });
}

describe("AllJourneysView — удаление из карточки поездки", () => {
  it("«⋯» → «Delete journey» спрашивает подтверждение с маршрутом; «Cancel» ничего не удаляет", async () => {
    const deleteSpy = vi.fn();
    server.use(
      http.delete("/v1/journeys/:journeyId/", () => {
        deleteSpy();
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const { user } = await openMoscowToLondonCard();

    const dialog = await openDeleteDialog(user);
    expect(within(dialog).getByText(/Moscow → London will disappear/u)).toBeInTheDocument();
    await user.click(within(dialog).getByRole("button", { name: "Cancel" }));

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(screen.getByRole("heading", { level: 1, name: "Moscow to London" })).toBeInTheDocument();
    expect(deleteSpy).not.toHaveBeenCalled();
  });

  it("«Delete» удаляет поездку и возвращает к ленте без её строки, фокус — на ленте", async () => {
    let deletedPath: string | null = null;
    server.use(
      http.delete("/v1/journeys/:journeyId/", ({ request }) => {
        deletedPath = new URL(request.url).pathname;
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const { user } = await openMoscowToLondonCard();

    await user.click(within(await openDeleteDialog(user)).getByRole("button", { name: "Delete" }));

    const year2021 = await screen.findByRole("region", { name: "2021" });
    expect(within(year2021).getAllByRole("listitem")).toHaveLength(1);
    expect(screen.queryByRole("heading", { level: 1, name: "Moscow to London" })).not.toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Journeys by year" })).toHaveFocus();
    expect(deletedPath).toBe(`/v1/journeys/${MOSCOW_TO_LONDON.journeyId}/`);
  });

  it("уже удалённая поездка (404 на DELETE) просто пропадает — цель достигнута", async () => {
    server.use(
      http.delete("/v1/journeys/:journeyId/", () =>
        HttpResponse.json({ code: "journeys.journey_not_found", message: "нет" }, { status: 404 }),
      ),
    );
    const { user } = await openMoscowToLondonCard();

    await user.click(within(await openDeleteDialog(user)).getByRole("button", { name: "Delete" }));

    const year2021 = await screen.findByRole("region", { name: "2021" });
    expect(within(year2021).getAllByRole("listitem")).toHaveLength(1);
    expect(screen.queryByText("This journey no longer exists")).not.toBeInTheDocument();
  });

  it("удаление не прошло — сообщение в диалоге, карточка остаётся", async () => {
    server.use(http.delete("/v1/journeys/:journeyId/", () => HttpResponse.error()));
    const { user } = await openMoscowToLondonCard();

    const dialog = await openDeleteDialog(user);
    await user.click(within(dialog).getByRole("button", { name: "Delete" }));

    expect(await within(dialog).findByText("Network error. Please try again.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "Moscow to London" })).toBeInTheDocument();
  });

  it("удалена последняя поездка выбранного года — его нет на шкале, выбор снят и лента показывает все годы", async () => {
    let journeys = FEED_JOURNEYS;
    serveFeedByYears(() => journeys);
    server.use(
      http.get("/v1/journeys/years/", () =>
        HttpResponse.json({ years: journeys.includes(PARIS_TO_MOSCOW) ? [2019, 2021] : [2021] }),
      ),
      http.delete("/v1/journeys/:journeyId/", () => {
        journeys = journeys.filter((journey) => journey !== PARIS_TO_MOSCOW);
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const { user } = renderAllJourneys();
    await screen.findByRole("region", { name: "2021" });
    screen.getByRole("slider", { name: "To year" }).focus();
    await user.keyboard("{ArrowLeft}{ArrowLeft}");
    await waitFor(() => expect(screen.queryByRole("region", { name: "2021" })).not.toBeInTheDocument());

    await user.click(await screen.findByRole("link", { name: /Paris to Moscow/u }));
    await screen.findByRole("heading", { level: 1, name: "Paris to Moscow" });
    await user.click(within(await openDeleteDialog(user)).getByRole("button", { name: "Delete" }));

    expect(await screen.findByRole("region", { name: "2021" })).toBeInTheDocument();
    expect(within(screen.getByRole("region", { name: "2021" })).getAllByRole("listitem")).toHaveLength(2);
    expect(screen.queryByRole("slider")).not.toBeInTheDocument();
    expect(screen.queryByText("No journeys match these filters")).not.toBeInTheDocument();
  });
});

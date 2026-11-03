import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { renderAddJourney, submitMoscowToLondon } from "../../test/addJourney";
import { GEO_CITIES, server } from "../../test/handlers";
import { screen, waitFor } from "../../test/render";

const [MOSCOW, LONDON] = GEO_CITIES;

const UNKNOWN_CITY_TEXT = "This city wasn't found. Pick it from the suggestions again";

/** The backend rejects cities with these ids as `journeys.unknown_city`. */
function respondRejectedCities(cityIds: string[]): void {
  server.use(
    http.post("/v1/journeys/", () =>
      HttpResponse.json(
        { code: "journeys.unknown_city", message: "ru", details: { city_ids: cityIds } },
        { status: 400 },
      ),
    ),
  );
}

describe("AddJourneyPage — ошибки бэка", () => {
  it("показывает ошибку уровня формы, когда создание поездки падает", async () => {
    server.use(http.post("/v1/journeys/", () => HttpResponse.error()));
    const { user } = renderAddJourney();

    await submitMoscowToLondon(user);

    expect(await screen.findByText("Network error. Please try again.")).toBeInTheDocument();
    expect(screen.queryByText("journeys-landing")).not.toBeInTheDocument();
  });

  it("рендерит ошибку года под полем года, а не теряет её", async () => {
    // Regression for two audit bugs at once: (1) journeys.* codes are mapped in the errors namespace
    // (otherwise a generic fallback would show); (2) details.field='year' lands on the real form
    // field (it used to send 'traveled_year', so setFieldError hit a phantom field and the text vanished).
    server.use(
      http.post("/v1/journeys/", () =>
        HttpResponse.json(
          { code: "journeys.date_in_future", message: "ru", details: { field: "year" } },
          { status: 400 },
        ),
      ),
    );
    const { user } = renderAddJourney();

    await submitMoscowToLondon(user);

    expect(await screen.findByText("The travel year can't be in the future")).toBeInTheDocument();
    expect(screen.queryByText("journeys-landing")).not.toBeInTheDocument();
  });

  it("город назначения, которого бэк не нашёл, подсвечивается под своим полем", async () => {
    respondRejectedCities([LONDON.cityId]);
    const { user } = renderAddJourney();

    await submitMoscowToLondon(user);

    const destinationError = await screen.findByText(UNKNOWN_CITY_TEXT);
    expect(screen.getAllByText(UNKNOWN_CITY_TEXT)).toHaveLength(1);
    // The error sits at the "To" field: its description references the error text.
    expect(screen.getByLabelText("To")).toHaveAccessibleDescription(destinationError.textContent ?? "");
    expect(screen.queryByText("journeys-landing")).not.toBeInTheDocument();
  });

  it("город отправления, которого бэк не нашёл, подсвечивается только под полем «Откуда»", async () => {
    respondRejectedCities([MOSCOW.cityId]);
    const { user } = renderAddJourney();

    await submitMoscowToLondon(user);

    const originError = await screen.findByText(UNKNOWN_CITY_TEXT);
    expect(screen.getByLabelText("From")).toHaveAccessibleDescription(originError.textContent ?? "");
    expect(screen.getByLabelText("To")).not.toHaveAccessibleDescription();
    expect(screen.queryByText("journeys-landing")).not.toBeInTheDocument();
  });

  it("если бэк не нашёл оба города, подсвечиваются оба поля", async () => {
    respondRejectedCities([MOSCOW.cityId, LONDON.cityId]);
    const { user } = renderAddJourney();

    await submitMoscowToLondon(user);

    await waitFor(() => expect(screen.getAllByText(UNKNOWN_CITY_TEXT)).toHaveLength(2));
  });

  it("ненайденный id не из формы — ошибка уровня формы, а не тишина", async () => {
    respondRejectedCities(["99999999-9999-4999-8999-999999999999"]);
    const { user } = renderAddJourney();

    await submitMoscowToLondon(user);

    expect(await screen.findByText(UNKNOWN_CITY_TEXT)).toBeInTheDocument();
    expect(screen.getByLabelText("From")).not.toHaveAccessibleDescription();
    expect(screen.getByLabelText("To")).not.toHaveAccessibleDescription();
  });
});

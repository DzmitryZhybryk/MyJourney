import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { getJourneysGlobeQueryKey, getJourneysMapQueryKey } from "../../api/sdk";
import { pickCity, pickOption, renderAddJourney, submitMoscowToLondon } from "../../test/addJourney";
import { GEO_CITIES, server } from "../../test/handlers";
import { createTestQueryClient, screen } from "../../test/render";
import { movementsQueryOptions } from "./movements/movementsQuery";

// Form scenarios are split across files (*.errors / *.validation / *.fields / *.scene): every
// city pick waits for the autocomplete debounce, and in one file they would run strictly in sequence.

const [MOSCOW, LONDON] = GEO_CITIES;

describe("AddJourneyPage — отправка", () => {
  it("создаёт поездку с id выбранных городов и ведёт в список поездок", async () => {
    let body: unknown = null;
    server.use(
      http.post("/v1/journeys/", async ({ request }) => {
        body = await request.json();
        return new HttpResponse(null, { status: 201 });
      }),
    );
    const { user } = renderAddJourney();

    await submitMoscowToLondon(user);

    expect(await screen.findByText("journeys-landing")).toBeInTheDocument();
    expect(body).toEqual({
      originCityId: MOSCOW.cityId,
      destinationCityId: LONDON.cityId,
      transportType: "air",
      traveledYear: 2020,
    });
  });

  it("успешное создание помечает устаревшими карту, глобус и карту перемещений при любых фильтрах", async () => {
    server.use(http.post("/v1/journeys/", () => new HttpResponse(null, { status: 201 })));
    const queryClient = createTestQueryClient();
    // Everything is already in the cache, as after visiting the tabs before adding a journey. The
    // movements map comes in two variants: unfiltered and with one transport type.
    const filteredMovementsKey = movementsQueryOptions(["air"]).queryKey;
    const noMovements = { firstYear: null, lastYear: null, connections: [] };
    queryClient.setQueryData(getJourneysMapQueryKey(), { countries: [] });
    queryClient.setQueryData(getJourneysGlobeQueryKey(), { cities: [] });
    queryClient.setQueryData(movementsQueryOptions().queryKey, noMovements);
    queryClient.setQueryData(filteredMovementsKey, noMovements);
    const { user } = renderAddJourney(queryClient);

    await submitMoscowToLondon(user);

    expect(await screen.findByText("journeys-landing")).toBeInTheDocument();
    expect(queryClient.getQueryState(getJourneysMapQueryKey())?.isInvalidated).toBe(true);
    expect(queryClient.getQueryState(getJourneysGlobeQueryKey())?.isInvalidated).toBe(true);
    expect(queryClient.getQueryState(movementsQueryOptions().queryKey)?.isInvalidated).toBe(true);
    expect(queryClient.getQueryState(filteredMovementsKey)?.isInvalidated).toBe(true);
  });

  it("провал создания карту не трогает — инвалидировать нечего", async () => {
    server.use(http.post("/v1/journeys/", () => HttpResponse.error()));
    const queryClient = createTestQueryClient();
    queryClient.setQueryData(getJourneysMapQueryKey(), { countries: [] });
    const { user } = renderAddJourney(queryClient);

    await submitMoscowToLondon(user);

    expect(await screen.findByText("Network error. Please try again.")).toBeInTheDocument();
    expect(queryClient.getQueryState(getJourneysMapQueryKey())?.isInvalidated).toBe(false);
  });

  it("кнопка swap меняет «откуда»/«куда» местами — в полях и в payload", async () => {
    let body: unknown = null;
    server.use(
      http.post("/v1/journeys/", async ({ request }) => {
        body = await request.json();
        return new HttpResponse(null, { status: 201 });
      }),
    );
    const { user } = renderAddJourney();

    await pickCity({ user, label: "From", query: "Mos", option: /Moscow/iu });
    await pickCity({ user, label: "To", query: "Lon", option: /London/iu });

    await user.click(screen.getByRole("button", { name: "Swap origin and destination" }));

    // The visible field text followed the swapped form values.
    expect(screen.getByLabelText("From")).toHaveValue("London");
    expect(screen.getByLabelText("To")).toHaveValue("Moscow");

    await pickOption({ user, trigger: screen.getByPlaceholderText("Choose transport"), option: "Air" });
    await pickOption({ user, trigger: screen.getByPlaceholderText("Select year"), option: "2020" });
    await user.click(screen.getByRole("button", { name: "Add journey" }));

    expect(await screen.findByText("journeys-landing")).toBeInTheDocument();
    expect(body).toMatchObject({ originCityId: LONDON.cityId, destinationCityId: MOSCOW.cityId });
  });
});

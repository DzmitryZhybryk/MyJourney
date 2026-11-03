import type { APIRequestContext } from "@playwright/test";

import { expect } from "../fixtures";

/** Finds a city via geo search and returns its `cityId`, the only thing journey creation accepts. */
export async function findCityId(request: APIRequestContext, token: string, searchText: string): Promise<string> {
  const response = await request.get("/v1/geo/cities/search/", {
    headers: { Authorization: `Bearer ${token}` },
    params: { searchText, language: "en", limit: 1 },
  });
  expect(response.ok(), `city search failed: ${response.status()} ${await response.text()}`).toBeTruthy();
  const { items } = (await response.json()) as { items: { cityId: string }[] };
  expect(items.length, `газеттир не нашёл «${searchText}»`).toBeGreaterThan(0);
  return items[0].cityId;
}

interface JourneyInput {
  originCityId: string;
  destinationCityId: string;
  transportType: "land" | "air" | "water";
  traveledYear: number;
}

/** Creates a journey via the API on behalf of the token owner. */
export async function createJourney(request: APIRequestContext, token: string, journey: JourneyInput): Promise<void> {
  const created = await request.post("/v1/journeys/", {
    headers: { Authorization: `Bearer ${token}` },
    data: journey,
  });
  expect(created.ok(), `create journey failed: ${created.status()} ${await created.text()}`).toBeTruthy();
}

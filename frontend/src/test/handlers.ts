/**
 * Reusable MSW handlers: the frontend's "API fakes".
 *
 * Default happy-path responses for all `/v1/auth/*` routes. A specific test overrides the case it
 * needs via `server.use(...)` (errors, conflicts) without touching the rest. The server starts and
 * stops in `src/test/setup.ts`.
 *
 * Unit tests do not use these: they install their own `fetch` mock via `vi.stubGlobal` and bypass
 * MSW (see `api/client.test.ts`). MSW works only at the component layer, where `fetch` is not replaced.
 */

import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

import type { CitySearchItem, CurrentUserResponse, JourneyFeedEntry, MovementsMapResponse } from "../api/sdk";

/**
 * Minimal gazetteer for autocomplete component tests (`/v1/geo/cities/search/`). Names are already
 * "resolved" (the backend returns them per language); the handler filters by prefix like the real
 * search. A test overrides the results via `server.use(...)` for an empty/error case.
 */
export const GEO_CITIES: readonly CitySearchItem[] = [
  // cityId must be a UUID: the SDK validates the response with the generated schema (`z.uuid()`)
  // and a "speaking" identifier from the fixture fails it.
  {
    cityId: "11111111-1111-4111-8111-111111111111",
    name: "Moscow",
    countryCode: "RU",
    latitude: 55.75,
    longitude: 37.62,
    population: 10_000_000,
  },
  {
    cityId: "22222222-2222-4222-8222-222222222222",
    name: "London",
    countryCode: "GB",
    latitude: 51.5,
    longitude: -0.12,
    population: 9_000_000,
  },
  {
    cityId: "33333333-3333-4333-8333-333333333333",
    name: "Paris",
    countryCode: "FR",
    latitude: 48.85,
    longitude: 2.35,
    population: 2_000_000,
  },
];

/** base64url encoding of a JWT payload segment (`+/` -> `-_`, no padding). */
function base64Url(value: string): string {
  return btoa(value)
    .replace(/\+/gu, "-")
    .replace(/\//gu, "_")
    .replace(/=+$/u, "");
}

type TokenClaims = {
  sub?: string;
  email_verified?: boolean;
  exp?: number;
};

/**
 * Builds a decodable `header.<payload>.signature` token with the given claims (the signature is
 * not checked: the frontend decodes the payload without verification, see `jwt.ts`).
 * `email_verified: true` by default so a successful login does not open the verify dialog in tests
 * that do not check it.
 */
export function makeAccessToken(claims: TokenClaims = {}): string {
  const payload = {
    sub: claims.sub ?? "user-test",
    email_verified: claims.email_verified ?? true,
    exp: claims.exp ?? 4_102_444_800, // 2100-01-01, safely in the future
  };

  return `header.${base64Url(JSON.stringify(payload))}.signature`;
}

/** Default token for successful login/register responses. */
export const TEST_ACCESS_TOKEN = makeAccessToken();

/**
 * Current user profile (`/v1/users/me/`). A test with another name or an error overrides the
 * response via `server.use(...)`.
 */
export const TEST_CURRENT_USER: CurrentUserResponse = {
  displayName: "traveler",
};

const successTokenBody = { accessToken: TEST_ACCESS_TOKEN, tokenType: "bearer" };

const [MOSCOW_POINT, LONDON_POINT, PARIS_POINT] = GEO_CITIES.map(({ cityId, latitude, longitude }) => ({
  cityId,
  latitude,
  longitude,
}));

/**
 * Movements map without a transport filter: Moscow -> London in 2019 and 2021, back in 2020 (one
 * arc, arrows at both ends) and London -> Paris in 2022: journeys from 2019 to 2022.
 */
export const MOVEMENTS_RESPONSE: MovementsMapResponse = {
  firstYear: 2019,
  lastYear: 2022,
  connections: [
    { origin: MOSCOW_POINT, destination: LONDON_POINT, years: [2019, 2021] },
    { origin: LONDON_POINT, destination: MOSCOW_POINT, years: [2020] },
    { origin: LONDON_POINT, destination: PARIS_POINT, years: [2022] },
  ],
};

const [MOSCOW_CITY, LONDON_CITY, PARIS_CITY] = GEO_CITIES.map(({ cityId, countryCode, latitude, longitude }) => ({
  cityId,
  countryCode,
  latitude,
  longitude,
}));

/**
 * Journey feed in one page: in 2021 Moscow -> London and London -> Paris, in 2019 Paris -> Moscow.
 * Years for the chips are `FEED_YEARS`.
 */
export const FEED_JOURNEYS: readonly JourneyFeedEntry[] = [
  {
    journeyId: "aaaaaaaa-0000-4000-8000-000000000001",
    origin: MOSCOW_CITY,
    destination: LONDON_CITY,
    transportType: "air",
    traveledYear: 2021,
    distanceKm: 2500,
  },
  {
    journeyId: "aaaaaaaa-0000-4000-8000-000000000002",
    origin: LONDON_CITY,
    destination: PARIS_CITY,
    transportType: "land",
    traveledYear: 2021,
    distanceKm: 344,
  },
  {
    journeyId: "aaaaaaaa-0000-4000-8000-000000000003",
    origin: PARIS_CITY,
    destination: MOSCOW_CITY,
    transportType: "air",
    traveledYear: 2019,
    distanceKm: 2480,
  },
];

export const FEED_YEARS: readonly number[] = [2019, 2021];

/** What the distance preview handler answers for any pair. */
export const ESTIMATED_DISTANCE_KM = 1234;

export const handlers = [
  http.post("/v1/auth/register/", () => HttpResponse.json(successTokenBody, { status: 201 })),
  http.post("/v1/auth/login/", () => HttpResponse.json(successTokenBody, { status: 200 })),
  http.post("/v1/auth/logout/", () => new HttpResponse(null, { status: 204 })),
  // Default: no session, so the bootstrap refresh in `AuthProvider` deterministically ends "not
  // logged in". A logged-in user test overrides it with 200.
  http.post("/v1/auth/refresh/", () =>
    HttpResponse.json(
      { code: "auth.invalid_refresh_token", message: "no session" },
      { status: 401 },
    ),
  ),
  // 202 "accepted for async processing" with an honestly empty body, as the backend returns it
  // (Response(status_code=202)); parseSuccess tolerates an empty body on any 2xx.
  http.post("/v1/auth/email/send-verification/", () => new HttpResponse(null, { status: 202 })),
  http.post("/v1/auth/email/verify/", () => new HttpResponse(null, { status: 204 })),
  // Geo autocomplete: prefix filtering of the fixture by searchText (mirrors the real search).
  http.get("/v1/geo/cities/search/", ({ request }) => {
    const query = (new URL(request.url).searchParams.get("searchText") ?? "").trim().toLowerCase();
    const items = GEO_CITIES.filter((city) => city.name.toLowerCase().startsWith(query));
    return HttpResponse.json({ items });
  }),
  // City names by id: knows only fixture cities and omits unknown ids, like the backend.
  http.post("/v1/geo/cities/resolve/", async ({ request }) => {
    const { cityIds } = (await request.json()) as { cityIds: string[] };
    const items = GEO_CITIES.filter((city) => cityIds.includes(city.cityId)).map((city) => ({
      cityId: city.cityId,
      name: city.name,
    }));
    return HttpResponse.json({ items });
  }),
  // Journey creation: 201 with no body (as the backend returns it).
  http.post("/v1/journeys/", () => new HttpResponse(null, { status: 201 })),
  // Journey map: the aggregate of visited countries (feeds WorldMap). A test overrides it with an
  // empty/error response via server.use(...).
  http.get("/v1/journeys/map/", () =>
    HttpResponse.json({
      countries: [
        {
          countryCode: "RU",
          cities: [{ cityId: GEO_CITIES[0].cityId, latitude: 55.75, longitude: 37.62, years: [2020, 2022] }],
        },
        {
          countryCode: "GB",
          cities: [{ cityId: GEO_CITIES[1].cityId, latitude: 51.5, longitude: -0.12, years: [2021] }],
        },
      ],
    }),
  ),
  // Cities for the globe: the same cities as the map, without countries and years.
  http.get("/v1/journeys/globe/", () =>
    HttpResponse.json({
      cities: [
        { cityId: GEO_CITIES[0].cityId, latitude: 55.75, longitude: 37.62 },
        { cityId: GEO_CITIES[1].cityId, latitude: 51.5, longitude: -0.12 },
      ],
    }),
  ),
  // Movements map without filters. A test overrides it with an empty/error/filtered response via
  // server.use(...).
  http.get("/v1/journeys/movements/", () => HttpResponse.json(MOVEMENTS_RESPONSE)),
  // The feed in one page and years for the chips. A test overrides pages, filters and errors via
  // server.use(...).
  http.get("/v1/journeys/", () => HttpResponse.json({ items: FEED_JOURNEYS, nextCursor: null })),
  http.get("/v1/journeys/years/", () => HttpResponse.json({ years: FEED_YEARS })),
  // Edit and delete: 204 with no body; move returns the neighbour's year (a test sets its own via server.use).
  http.get("/v1/journeys/distance/", () => HttpResponse.json({ distanceKm: ESTIMATED_DISTANCE_KM })),
  http.put("/v1/journeys/:journeyId/", () => new HttpResponse(null, { status: 204 })),
  http.delete("/v1/journeys/:journeyId/", () => new HttpResponse(null, { status: 204 })),
  http.post("/v1/journeys/:journeyId/move/", () => HttpResponse.json({ traveledYear: 2021 })),
  // Current user profile: feeds CurrentUserProvider on any logged-in render.
  http.get("/v1/users/me/", () => HttpResponse.json(TEST_CURRENT_USER)),
];

export const server = setupServer(...handlers);

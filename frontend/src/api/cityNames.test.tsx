import { QueryClientProvider, type QueryClient } from "@tanstack/react-query";
import { renderHook } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it } from "vitest";

import { i18n } from "../i18n";
import { GEO_CITIES, server } from "../test/handlers";
import { act, createTestQueryClient, waitFor } from "../test/render";
import { cityLabel, useCityNames } from "./cityNames";

const [MOSCOW, LONDON, PARIS] = GEO_CITIES;
const UNKNOWN_ID = "99999999-9999-4999-8999-999999999999";

type ResolveBody = { cityIds: string[]; language: string };

/** Replaces `resolve` with the same fake but records request bodies. */
function recordResolveRequests(): ResolveBody[] {
  const bodies: ResolveBody[] = [];
  server.use(
    http.post("/v1/geo/cities/resolve/", async ({ request }) => {
      const body = (await request.json()) as ResolveBody;
      bodies.push(body);
      const items = GEO_CITIES.filter((city) => body.cityIds.includes(city.cityId)).map((city) => ({
        cityId: city.cityId,
        name: city.name,
      }));
      return HttpResponse.json({ items });
    }),
  );
  return bodies;
}

function wrapperFor(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

function renderCityNames(cityIds: string[], queryClient: QueryClient = createTestQueryClient()) {
  return renderHook(({ ids }: { ids: string[] }) => useCityNames(ids), {
    initialProps: { ids: cityIds },
    wrapper: wrapperFor(queryClient),
  });
}

afterEach(async () => {
  // The language is a global i18n singleton: restore en so tests do not affect each other.
  await i18n.changeLanguage("en");
});

describe("useCityNames", () => {
  it("отдаёт название известного города и null для города, которого geo не знает", async () => {
    const { result } = renderCityNames([MOSCOW.cityId, UNKNOWN_ID]);

    await waitFor(() => expect(result.current(MOSCOW.cityId)).toBe("Moscow"));
    expect(result.current(UNKNOWN_ID)).toBeNull();
  });

  it("пока названия грузятся, отдаёт undefined, а не «неизвестно»", () => {
    const { result } = renderCityNames([MOSCOW.cityId]);

    expect(result.current(MOSCOW.cityId)).toBeUndefined();
  });

  it("без id в geo не ходит", () => {
    const bodies = recordResolveRequests();
    const queryClient = createTestQueryClient();
    const { result } = renderCityNames([], queryClient);

    // The query is disabled at once: the client loads nothing and nothing went to geo.
    expect(queryClient.isFetching()).toBe(0);
    expect(bodies).toHaveLength(0);
    expect(result.current(MOSCOW.cityId)).toBeUndefined();
  });

  it("одни и те же города в другом порядке и с повторами — один запрос на всех", async () => {
    const bodies = recordResolveRequests();
    const queryClient = createTestQueryClient();
    const first = renderCityNames([MOSCOW.cityId, LONDON.cityId], queryClient);
    const second = renderCityNames([LONDON.cityId, MOSCOW.cityId, LONDON.cityId], queryClient);

    await waitFor(() => expect(first.result.current(LONDON.cityId)).toBe("London"));
    expect(second.result.current(MOSCOW.cityId)).toBe("Moscow");
    expect(bodies).toHaveLength(1);
  });

  it("больше 1000 id режет на запросы по 1000", async () => {
    const bodies = recordResolveRequests();
    const manyIds = Array.from(
      { length: 1500 },
      (_, index) => `00000000-0000-4000-8000-${String(index).padStart(12, "0")}`,
    );
    const { result } = renderCityNames([...manyIds, MOSCOW.cityId]);

    await waitFor(() => expect(result.current(MOSCOW.cityId)).toBe("Moscow"));
    expect(bodies.map((body) => body.cityIds.length).sort((left, right) => right - left)).toEqual([1000, 501]);
  });

  it("новый город, пока догружается, — undefined, а прошлые названия остаются", async () => {
    const queryClient = createTestQueryClient();
    const { result, rerender } = renderCityNames([MOSCOW.cityId], queryClient);
    await waitFor(() => expect(result.current(MOSCOW.cityId)).toBe("Moscow"));

    // Hold the response for the second set to catch the intermediate state.
    let release: () => void = () => {};
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    server.use(
      http.post("/v1/geo/cities/resolve/", async () => {
        await gate;
        return HttpResponse.json({ items: [{ cityId: MOSCOW.cityId, name: "Moscow" }] });
      }),
    );
    rerender({ ids: [MOSCOW.cityId, PARIS.cityId] });

    expect(result.current(MOSCOW.cityId)).toBe("Moscow");
    expect(result.current(PARIS.cityId)).toBeUndefined();

    release();
    // The response came without Paris: now it really is "unknown".
    await waitFor(() => expect(result.current(PARIS.cityId)).toBeNull());
  });

  it("при смене языка интерфейса просит названия на новом языке", async () => {
    const bodies = recordResolveRequests();
    const { result } = renderCityNames([MOSCOW.cityId]);
    await waitFor(() => expect(result.current(MOSCOW.cityId)).toBe("Moscow"));

    await act(async () => {
      await i18n.changeLanguage("ru");
    });

    await waitFor(() => expect(bodies.map((body) => body.language)).toEqual(["en", "ru"]));
  });
});

describe("cityLabel", () => {
  it("название показывает как есть, неизвестный город — подписью «неизвестно», загрузку — никак", () => {
    expect(cityLabel("Moscow", "Unknown city")).toBe("Moscow");
    expect(cityLabel(null, "Unknown city")).toBe("Unknown city");
    expect(cityLabel(undefined, "Unknown city")).toBeUndefined();
  });
});

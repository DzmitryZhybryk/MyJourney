import { http, HttpResponse } from "msw";
import { useMemo, useRef, type ReactElement } from "react";
import { Link, Outlet, Route, Routes } from "react-router";

import type { JourneyFeedEntry } from "../api/sdk";
import { AllJourneysView } from "../pages/journeys/all/AllJourneysView";
import type { JourneysOutletContext } from "../pages/journeys/JourneysLayout";
import { JourneysMapHost } from "../pages/journeys/map/JourneysMapHost";
import { JourneysMapSceneProvider } from "../pages/journeys/map/JourneysMapSceneProvider";
import { FEED_JOURNEYS, server } from "./handlers";
import { renderWithProviders, screen, within } from "./render";

/**
 * Serves the feed in one page filtered by `yearFrom` / `yearTo` like the backend, from what
 * `journeys()` returns at request time (a test changes it after a save or a delete). Returns the
 * recorded request queries.
 */
export function serveFeedByYears(journeys: () => readonly JourneyFeedEntry[] = () => FEED_JOURNEYS): URLSearchParams[] {
  const requests: URLSearchParams[] = [];
  server.use(
    http.get("/v1/journeys/", ({ request }) => {
      const params = new URL(request.url).searchParams;
      requests.push(params);
      const yearFrom = Number(params.get("yearFrom") ?? Number.NEGATIVE_INFINITY);
      const yearTo = Number(params.get("yearTo") ?? Number.POSITIVE_INFINITY);
      const items = journeys().filter((journey) => journey.traveledYear >= yearFrom && journey.traveledYear <= yearTo);
      return HttpResponse.json({ items, nextCursor: null });
    }),
  );
  return requests;
}

export interface JourneysTab {
  path: string;
  /** `null`: a screen with no content of its own, as the wishlist placeholder in App.tsx. */
  element: ReactElement | null;
}

/**
 * The part of the Journeys shell a tab depends on: the shared map with its scene channel and the
 * panel ref passed through `<Outlet context>`. Without the header, so no auth or user request.
 * A link per path (named by the path) lets a test switch tabs the way a user does.
 */
function JourneysMapShell({ paths }: { paths: readonly string[] }) {
  const panelRef = useRef<HTMLElement>(null);
  const context = useMemo<JourneysOutletContext>(() => ({ panelRef }), []);
  return (
    <JourneysMapSceneProvider>
      <nav>
        {paths.map((path) => (
          <Link key={path} to={path}>
            {path}
          </Link>
        ))}
      </nav>
      <JourneysMapHost />
      <Outlet context={context} />
    </JourneysMapSceneProvider>
  );
}

/**
 * The feed tab alone, as its scenario-split test files render it, with its card route (as in
 * App.tsx); `route` opens a journey card by its address.
 */
export function renderAllJourneys(route = "/journeys/all") {
  return renderJourneysTabs([{ path: "/journeys/all/:journeyId?", element: <AllJourneysView /> }], route);
}

/** Opens the feed, then the Moscow -> London card (`FEED_JOURNEYS[0]`) by clicking its row. */
export async function openMoscowToLondonCard() {
  const rendered = renderAllJourneys();
  const year2021 = await screen.findByRole("region", { name: "2021" });
  await rendered.user.click(await within(year2021).findByRole("link", { name: /Moscow to London/u }));
  await screen.findByRole("heading", { level: 1, name: "Moscow to London" });
  return rendered;
}

/** Renders Journeys tabs under the shared map, starting at `route` (the first tab by default). */
export function renderJourneysTabs(tabs: readonly JourneysTab[], route = tabs[0].path) {
  return renderWithProviders(
    <Routes>
      <Route element={<JourneysMapShell paths={tabs.map((tab) => tab.path)} />}>
        {tabs.map((tab) => (
          <Route key={tab.path} path={tab.path} element={tab.element} />
        ))}
      </Route>
    </Routes>,
    { route },
  );
}

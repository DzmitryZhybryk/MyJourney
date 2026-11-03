import {
  listJourneysInfiniteOptions,
  zTransportTypeEnum,
  type JourneyFeedEntry,
  type JourneysFeedResponse,
  type ListJourneysData,
  type TransportTypeEnum,
} from "../../../api/sdk";
import type { YearRange } from "./yearRange";

export interface FeedFilters {
  yearRange: YearRange | null;
  transportTypes: readonly TransportTypeEnum[];
}

/** Filters under which the feed is all journeys: its cache is the source for client-side selection. */
export const NO_FEED_FILTERS: FeedFilters = { yearRange: null, transportTypes: zTransportTypeEnum.options };

// The year slider changes the filter on every year passed. The filtered feed goes to the network
// once the filter has stood this long: a request for a superseded filter is cancelled before sending.
const FILTER_SETTLE_MS = 250;

/** Waits for the filter to settle; aborting the request interrupts the wait. */
function waitForFilterToSettle(signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(resolve, FILTER_SETTLE_MS);
    signal.addEventListener(
      "abort",
      () => {
        clearTimeout(timer);
        reject(signal.reason);
      },
      { once: true },
    );
  });
}

/** Journeys of one year in feed order. */
export interface FeedYearGroup {
  year: number;
  journeys: readonly JourneyFeedEntry[];
}

/**
 * Infinite feed query options: the only place where filters become a key.
 *
 * The same transport set gives the same key in any selection order, and "all selected" equals "no
 * filter". The first page has no cursor: an empty object, not `null`, because the generated
 * `queryFn` takes an object as request parameters. The response never goes stale by itself;
 * journey changes invalidate it.
 *
 * The first page of a filtered feed waits for the filter to settle: if it changed meanwhile, the
 * request is cancelled (Query cancels a request nobody awaits anymore since `queryFn` took the signal).
 */
export function feedQueryOptions({ yearRange, transportTypes }: FeedFilters) {
  const query: NonNullable<ListJourneysData["query"]> = {};
  if (yearRange) {
    [query.yearFrom, query.yearTo] = yearRange;
  }

  if (transportTypes.length < zTransportTypeEnum.options.length) {
    query.transportType = [...transportTypes].sort();
  }

  const options = {
    ...listJourneysInfiniteOptions({ query }),
    initialPageParam: {},
    getNextPageParam: (lastPage: JourneysFeedResponse) => lastPage.nextCursor ?? undefined,
    staleTime: Infinity,
  };
  const fetchPage = options.queryFn;
  if (Object.keys(query).length === 0 || typeof fetchPage !== "function") {
    return options;
  }

  return {
    ...options,
    queryFn: async (context: Parameters<typeof fetchPage>[0]) => {
      // The first page is a params object, later ones are a cursor string.
      if (typeof context.pageParam === "object") {
        await waitForFilterToSettle(context.signal);
      }

      return fetchPage(context);
    },
  };
}

/**
 * The feed by filters, built on the client from already loaded pages; shown until the server
 * answers. Returns pages with only the rows matching the filters.
 *
 * Row order is the same the server will return: a filter only drops rows. The selection has no
 * cursors, so there is nothing to load more with; it lives until the answer.
 */
export function filterFeedPages(
  pages: readonly JourneysFeedResponse[],
  { yearRange, transportTypes }: FeedFilters,
): JourneysFeedResponse[] {
  const isShown = (journey: JourneyFeedEntry) =>
    transportTypes.includes(journey.transportType) &&
    (!yearRange || (journey.traveledYear >= yearRange[0] && journey.traveledYear <= yearRange[1]));

  return pages.map((page) => ({ items: page.items.filter(isShown), nextCursor: null }));
}

/**
 * Whether the feed is loaded to the end: then a client-side selection from it equals the server's
 * answer. `pages` is `undefined` if the feed is not in the cache; returns `true` if there are no more pages.
 */
export function isFeedFullyLoaded(pages: readonly JourneysFeedResponse[] | undefined): boolean {
  const lastPage = pages?.at(-1);
  return lastPage !== undefined && !lastPage.nextCursor;
}

/**
 * Groups the loaded feed pages by year (pages in load order).
 *
 * A journey that landed in two pages (rows shifted between requests) is shown once, where it was
 * first met. Years go in order of first appearance, i.e. as in the feed.
 */
export function groupFeedByYear(pages: readonly JourneysFeedResponse[]): readonly FeedYearGroup[] {
  const seen = new Set<string>();
  const groups = new Map<number, JourneyFeedEntry[]>();
  for (const journey of pages.flatMap((page) => page.items)) {
    if (seen.has(journey.journeyId)) {
      continue;
    }

    seen.add(journey.journeyId);
    const group = groups.get(journey.traveledYear);
    if (group) {
      group.push(journey);
    } else {
      groups.set(journey.traveledYear, [journey]);
    }
  }

  return [...groups].map(([year, journeys]) => ({ year, journeys }));
}

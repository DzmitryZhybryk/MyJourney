import type { InfiniteData, QueryClient } from "@tanstack/react-query";

import {
  getJourneysGlobeQueryKey,
  getJourneysMapQueryKey,
  getJourneyYearsQueryKey,
  getMovementsMapQueryKey,
  listJourneysInfiniteQueryKey,
  type JourneysFeedResponse,
} from "../../api/sdk";

/*
 * A key without parameters matches the keys for any filters, so all variants of the movements map
 * and feed are invalidated. All of it lives with `staleTime: Infinity`, so without an explicit
 * invalidation a changed journey would not show up until a page reload.
 */

/** Invalidates everything built from journeys except the feed: maps, globe, years. */
export function invalidateJourneyAggregates(queryClient: QueryClient): Promise<unknown> {
  return Promise.all([
    queryClient.invalidateQueries({ queryKey: getJourneysMapQueryKey() }),
    queryClient.invalidateQueries({ queryKey: getJourneysGlobeQueryKey() }),
    queryClient.invalidateQueries({ queryKey: getMovementsMapQueryKey() }),
    queryClient.invalidateQueries({ queryKey: getJourneyYearsQueryKey() }),
  ]);
}

/**
 * Invalidates all loaded feed variants.
 *
 * `refetchType` picks which to refetch immediately: `"active"` includes the shown feed,
 * `"inactive"` only hidden ones (the shown feed stays as is until the next refresh).
 */
export function invalidateJourneyFeed(
  queryClient: QueryClient,
  refetchType: "active" | "inactive" = "active",
): Promise<void> {
  return queryClient.invalidateQueries({ queryKey: listJourneysInfiniteQueryKey(), refetchType });
}

/**
 * Removes a journey from all loaded feed variants without a request.
 *
 * Cursors of the next pages stay valid: they point at the last row of their page, not at a
 * position number.
 */
export function removeJourneyFromFeed(queryClient: QueryClient, journeyId: string): void {
  queryClient.setQueriesData<InfiniteData<JourneysFeedResponse>>(
    { queryKey: listJourneysInfiniteQueryKey() },
    (data) =>
      data && {
        ...data,
        pages: data.pages.map((page) => ({
          ...page,
          items: page.items.filter((journey) => journey.journeyId !== journeyId),
        })),
      },
  );
}

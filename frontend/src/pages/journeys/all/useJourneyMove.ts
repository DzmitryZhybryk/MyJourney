import { useMutation, useQueryClient, type InfiniteData, type QueryKey } from "@tanstack/react-query";
import { useState } from "react";

import { ApiError, errorCodeToken } from "../../../api/errors";
import { moveJourneyMutation, type JourneyFeedEntry, type JourneysFeedResponse } from "../../../api/sdk";
import { invalidateJourneyAggregates, invalidateJourneyFeed } from "../journeyCache";
import { moveJourneyInPages, type MoveTarget } from "./feedMove";

/**
 * Moves a journey with an optimistic reorder in the feed. `feedKey` is the shown feed's key (the
 * one reordered). Returns `move`, the in-progress flag and the last move's error token.
 *
 * The row takes its new place immediately, before the answer. The server places it flush with the
 * neighbour, so the shown feed is already right after success and is not refetched; only hidden
 * feed variants (other filters) are invalidated. If the backend refuses (neighbour deleted, not
 * ours), the feed reverts, shows an error and is refetched: a refusal means it diverged from the
 * server. Maps and years are invalidated only if the year changed: order within a year does not affect them.
 */
export function useJourneyMove(feedKey: QueryKey) {
  const queryClient = useQueryClient();
  const [errorToken, setErrorToken] = useState<string | null>(null);
  const { mutateAsync, isPending } = useMutation(moveJourneyMutation());

  const move = async (journey: JourneyFeedEntry, target: MoveTarget) => {
    setErrorToken(null);
    // A feed request returning after the reorder would overwrite it with the old order.
    await queryClient.cancelQueries({ queryKey: feedKey });
    const previous = queryClient.getQueryData<InfiniteData<JourneysFeedResponse>>(feedKey);
    queryClient.setQueryData<InfiniteData<JourneysFeedResponse>>(
      feedKey,
      (data) => data && { ...data, pages: moveJourneyInPages(data.pages, journey.journeyId, target) },
    );

    try {
      const result = await mutateAsync({
        path: { journey_id: journey.journeyId },
        body: { neighborJourneyId: target.neighborJourneyId, placement: target.placement },
      });
      if (result.traveledYear !== journey.traveledYear) {
        void invalidateJourneyAggregates(queryClient);
      }

      void invalidateJourneyFeed(queryClient, "inactive");
    } catch (err) {
      queryClient.setQueryData(feedKey, previous);
      setErrorToken(errorCodeToken(err instanceof ApiError ? err.code : "network"));
      void invalidateJourneyFeed(queryClient);
    }
  };

  return { move, isMoving: isPending, errorToken };
}

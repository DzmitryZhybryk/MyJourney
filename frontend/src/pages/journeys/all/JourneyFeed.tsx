import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type Announcements,
  type DragEndEvent,
  type DragOverEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { SortableContext, sortableKeyboardCoordinates } from "@dnd-kit/sortable";
import { Button, Loader, Text } from "@mantine/core";
import { useInfiniteQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { cityLabel, useCityNames } from "../../../api/cityNames";
import { resolveErrorToken } from "../../../api/errors";
import type { JourneyFeedEntry, JourneysFeedResponse, TransportTypeEnum } from "../../../api/sdk";
import {
  feedSortingStrategy,
  moveJourneyInPages,
  resolveMoveTarget,
  yearHeaderShift,
  type MoveTarget,
} from "./feedMove";
import { feedQueryOptions, filterFeedPages, groupFeedByYear, isFeedFullyLoaded, NO_FEED_FILTERS } from "./feedQuery";
import { JourneyFeedRow } from "./JourneyFeedRow";
import { useFlip } from "./motion";
import { useDistanceFormat } from "./useDistanceFormat";
import { useJourneyMove } from "./useJourneyMove";
import { YearHeader } from "./YearHeader";
import type { YearRange } from "./yearRange";

/**
 * Where the feed's own data stands: `pending` until the server has answered for these filters
 * (rows built from another variant are placeholders), `error` when the first page failed.
 */
export type FeedStatus = "pending" | "loaded" | "error";

interface JourneyFeedProps {
  yearRange: YearRange | null;
  transportTypes: readonly TransportTypeEnum[];
  /** Whether the user has any journeys at all: tells "empty so far" from "the filter found nothing". */
  hasJourneys: boolean;
  /** The feed sits under `display: none` behind the journey card. */
  isHidden: boolean;
  /** Loaded rows in display order; the map builds its frame from them, the card looks its journey up. */
  onJourneysChange: (journeys: readonly JourneyFeedEntry[]) => void;
  onStatusChange: (status: FeedStatus) => void;
  /** The journey the user is on: dragging, hovering or focusing. */
  onActiveJourneyChange: (journey: JourneyFeedEntry | null) => void;
}

/**
 * Feed of journeys by year with infinite scroll and drag and drop; a row opens the journey card.
 *
 * The next page loads when about half a screen remains to the end of the loaded rows: an
 * invisible sentinel is stretched upward from the list bottom. While a feed request or a move is
 * in flight the sentinel stays quiet, since loading more would cancel the refresh of what is
 * already loaded. On a filter change the previous rows stay on screen dimmed until the new set
 * arrives; they cannot be dragged meanwhile.
 *
 * All rows are one drag list, so a row can be moved to another year too; at the feed edge the
 * list scrolls by itself and the sentinel loads the following years.
 */
export function JourneyFeed({
  yearRange,
  transportTypes,
  hasJourneys,
  isHidden,
  onJourneysChange,
  onStatusChange,
  onActiveJourneyChange,
}: JourneyFeedProps) {
  const { t } = useTranslation("journeys");
  const { t: tCommon } = useTranslation("common");
  const queryClient = useQueryClient();
  const filters = { yearRange, transportTypes };
  const options = feedQueryOptions(filters);
  // Until the server answers for the new filters the feed is built from what is loaded: the
  // unfiltered feed has the most rows, otherwise take what was on screen.
  const allJourneysFeed = queryClient.getQueryData(feedQueryOptions(NO_FEED_FILTERS).queryKey);
  const feed = useInfiniteQuery({
    ...options,
    // A selection has no cursors: it is not paged further and lives until the server answers.
    placeholderData: (previous) => {
      const pages = (allJourneysFeed ?? previous)?.pages;
      return pages && { pages: filterFeedPages(pages, filters), pageParams: pages.map(() => null) };
    },
  });
  const { data, hasNextPage, isFetching, isFetchNextPageError, fetchNextPage } = feed;
  // A selection from a fully loaded feed equals the server's answer, so it is not dimmed.
  const isStale = feed.isPlaceholderData && !isFeedFullyLoaded(allJourneysFeed?.pages);
  const { move, isMoving, errorToken: moveErrorToken } = useJourneyMove(options.queryKey);

  // The Query cache delivers the reorder to the feed one render later, while dnd-kit drops the row
  // offsets immediately on release, so rows would jump back for a frame. Therefore put the dropped
  // row in its new place ourselves while the feed still shows the same pages the move was computed from.
  const [drop, setDrop] = useState<{ pages: readonly JourneysFeedResponse[]; journeyId: string; target: MoveTarget } | null>(
    null,
  );
  const pages = data?.pages;
  const isDropShown = drop !== null && drop.pages === pages;
  const shownPages = useMemo(
    () => (drop !== null && drop.pages === pages ? moveJourneyInPages(drop.pages, drop.journeyId, drop.target) : (pages ?? [])),
    [drop, pages],
  );
  const groups = useMemo(() => groupFeedByYear(shownPages), [shownPages]);
  const journeys = useMemo(() => groups.flatMap((group) => group.journeys), [groups]);
  const journeyIds = useMemo(() => journeys.map((journey) => journey.journeyId), [journeys]);
  const nameOf = useCityNames(journeys.flatMap((journey) => [journey.origin.cityId, journey.destination.cityId]));
  const distanceFormat = useDistanceFormat();

  const [dropYear, setDropYear] = useState<number | null>(null);
  const [dragId, setDragId] = useState<string | null>(null);
  // Which row the dragged one is over and its height: year headings shift by them.
  const [dragOver, setDragOver] = useState<{ overId: string; rowHeight: number } | null>(null);
  const [hoverId, setHoverId] = useState<string | null>(null);
  const isDragDisabled = isMoving || feed.isPlaceholderData;

  const containerRef = useRef<HTMLDivElement>(null);
  // The dropped row already stands where it is seen; FLIP only records the new positions,
  // otherwise it would replay the move again from the old spot.
  useFlip(containerRef, dragId !== null || isDropShown, isHidden);

  // The row under the cursor or with focus inside, via one listener for the whole feed. Focus moving
  // to a neighbouring button of the same row does not change the row.
  const hasRows = groups.length > 0;
  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }

    const rowIdOf = (target: EventTarget | null) =>
      target instanceof Element ? (target.closest<HTMLElement>("[data-flip-id]")?.dataset.flipId ?? null) : null;
    const handleEnter = (event: Event) => setHoverId(rowIdOf(event.target));
    const handlePointerLeave = () => setHoverId(null);
    const handleFocusOut = (event: FocusEvent) => {
      if (!(event.relatedTarget instanceof Node && container.contains(event.relatedTarget))) {
        setHoverId(null);
      }
    };
    container.addEventListener("pointerover", handleEnter);
    container.addEventListener("focusin", handleEnter);
    container.addEventListener("pointerleave", handlePointerLeave);
    container.addEventListener("focusout", handleFocusOut);

    return () => {
      container.removeEventListener("pointerover", handleEnter);
      container.removeEventListener("focusin", handleEnter);
      container.removeEventListener("pointerleave", handlePointerLeave);
      container.removeEventListener("focusout", handleFocusOut);
    };
  }, [hasRows]);

  const activeId = dragId ?? hoverId;
  const activeJourney = journeys.find((journey) => journey.journeyId === activeId) ?? null;
  let status: FeedStatus = "loaded";
  if (feed.isPending || feed.isPlaceholderData) {
    status = "pending";
  } else if (feed.isError && !data) {
    status = "error";
  }
  // Layout effects: a card opened by its address replaces the feed before the first paint,
  // instead of one frame of the full list.
  useLayoutEffect(() => {
    onJourneysChange(journeys);
  }, [journeys, onJourneysChange]);
  useLayoutEffect(() => {
    onStatusChange(status);
  }, [status, onStatusChange]);
  useEffect(() => {
    onActiveJourneyChange(activeJourney);
  }, [activeJourney, onActiveJourneyChange]);

  // A row is dragged only by its handle, so the pointer sensor needs no delay: the handle has
  // `touch-action: none`, and a finger does not scroll the page instead of dragging.
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const unknownLabel = tCommon("map.unknownCity");
  const routeOf = (journeyId: string | number) => {
    const journey = journeys.find((item) => item.journeyId === journeyId);
    if (!journey) {
      return "";
    }

    const origin = cityLabel(nameOf(journey.origin.cityId), unknownLabel) ?? "…";
    const destination = cityLabel(nameOf(journey.destination.cityId), unknownLabel) ?? "…";
    return `${origin} → ${destination}`;
  };
  const targetYearOf = (activeId: string | number, overId: string | number) =>
    resolveMoveTarget(journeys, String(activeId), String(overId))?.traveledYear ??
    journeys.find((journey) => journey.journeyId === activeId)?.traveledYear;
  // Without custom announcements a screen reader would read row ids.
  const announcements: Announcements = {
    onDragStart: ({ active }) => t("all.dnd.start", { route: routeOf(active.id) }),
    onDragOver: ({ active, over }) =>
      over ? t("all.dnd.over", { route: routeOf(over.id), year: targetYearOf(active.id, over.id) }) : undefined,
    onDragEnd: ({ active, over }) =>
      over ? t("all.dnd.end", { route: routeOf(active.id), year: targetYearOf(active.id, over.id) }) : undefined,
    onDragCancel: ({ active }) => t("all.dnd.cancel", { route: routeOf(active.id) }),
  };

  const handleDragStart = ({ active }: DragStartEvent) => {
    setDragId(String(active.id));
    setDropYear(journeys.find((journey) => journey.journeyId === active.id)?.traveledYear ?? null);
  };

  const handleDragOver = ({ active, over }: DragOverEvent) => {
    if (over) {
      // Take the height here: at drag start dnd-kit has not measured the row yet.
      setDragOver({ overId: String(over.id), rowHeight: active.rect.current.initial?.height ?? 0 });
      setDropYear(targetYearOf(active.id, over.id) ?? null);
    }
  };

  const handleDragEnd = ({ active, over }: DragEndEvent) => {
    setDragId(null);
    setDragOver(null);
    setDropYear(null);
    const journey = journeys.find((item) => item.journeyId === active.id);
    const target = over ? resolveMoveTarget(journeys, String(active.id), String(over.id)) : null;
    if (journey && target && pages) {
      setDrop({ pages, journeyId: journey.journeyId, target });
      void move(journey, target);
    }
  };

  const handleDragCancel = () => {
    setDragId(null);
    setDragOver(null);
    setDropYear(null);
  };

  const sentinelRef = useRef<HTMLDivElement>(null);
  const canLoadMore = hasNextPage && !isFetching && !isMoving && !isFetchNextPageError;
  // The observer is recreated when loading more is allowed again: if the sentinel is still on
  // screen, the new observer reports it immediately and requests the next page.
  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel || !canLoadMore) {
      return;
    }

    const observer = new IntersectionObserver((entries) => {
      if (entries.some((entry) => entry.isIntersecting)) {
        void fetchNextPage();
      }
    });
    observer.observe(sentinel);

    return () => observer.disconnect();
  }, [canLoadMore, fetchNextPage]);

  if (feed.isPending) {
    return (
      <output className="all-journeys__status">
        <Loader size="sm" color="gray" />
        <Text size="sm" c="var(--text-muted)">
          {t("all.loading")}
        </Text>
      </output>
    );
  }

  if (feed.isError && !data) {
    return (
      <div className="all-journeys__status" role="alert">
        <Text size="sm" fw={500} c="var(--text-error)">
          {t("all.error")}
        </Text>
        <Button size="xs" variant="subtle" color="gray" loading={isFetching} onClick={() => void feed.refetch()}>
          {t("all.retry")}
        </Button>
      </div>
    );
  }

  if (groups.length === 0) {
    return hasJourneys ? (
      <output className="all-journeys__status">
        <Text size="sm" c="var(--text-muted)">
          {t("all.noMatches")}
        </Text>
      </output>
    ) : (
      <output className="all-journeys__status">
        <Text size="sm" c="var(--text-muted)">
          {t("all.empty")}
        </Text>
        <Link to="/journeys/add" className="all-journeys__add-link">
          {t("all.addFirst")}
        </Link>
      </output>
    );
  }

  return (
    <div
      ref={containerRef}
      className={["journey-feed", isStale && "journey-feed--stale", dragId !== null && "journey-feed--sorting"]
        .filter(Boolean)
        .join(" ")}
      aria-busy={isFetching}
    >
      {moveErrorToken && (
        <Text size="sm" fw={500} c="var(--text-error)" className="journey-feed__error" role="alert">
          {resolveErrorToken(moveErrorToken)}
        </Text>
      )}

      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        accessibility={{ announcements, screenReaderInstructions: { draggable: t("all.dnd.instructions") } }}
        onDragStart={handleDragStart}
        onDragOver={handleDragOver}
        onDragEnd={handleDragEnd}
        onDragCancel={handleDragCancel}
      >
        <SortableContext items={journeyIds} strategy={feedSortingStrategy}>
          {groups.map((group) => {
            const headerId = `journey-year-${group.year}`;
            const headerShift =
              dragId === null || dragOver === null
                ? 0
                : yearHeaderShift({
                    activeIndex: journeyIds.indexOf(dragId),
                    overIndex: journeyIds.indexOf(dragOver.overId),
                    firstRowIndex: journeyIds.indexOf(group.journeys[0].journeyId),
                    height: dragOver.rowHeight,
                  });
            return (
              <section key={group.year} className="journey-feed__year" aria-labelledby={headerId}>
                <YearHeader id={headerId} year={group.year} shift={headerShift} />
                <ol className="journey-feed__rows">
                  {group.journeys.map((journey) => (
                    <JourneyFeedRow
                      key={journey.journeyId}
                      journey={journey}
                      nameOf={nameOf}
                      distanceFormat={distanceFormat}
                      isDragDisabled={isDragDisabled}
                      dropYear={dropYear}
                    />
                  ))}
                </ol>
              </section>
            );
          })}
        </SortableContext>
      </DndContext>

      {feed.isFetchingNextPage && (
        <div className="journey-feed__more">
          <Loader size="xs" color="gray" />
        </div>
      )}
      {isFetchNextPageError && (
        <div className="journey-feed__more" role="alert">
          <Text size="sm" fw={500} c="var(--text-error)">
            {t("all.loadMoreError")}
          </Text>
          <Button size="xs" variant="subtle" color="gray" onClick={() => void fetchNextPage()}>
            {t("all.retry")}
          </Button>
        </div>
      )}
      <div ref={sentinelRef} className="journey-feed__sentinel" aria-hidden="true" />
    </div>
  );
}

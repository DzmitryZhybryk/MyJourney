import type { SortingStrategy } from "@dnd-kit/sortable";

import type { JourneyFeedEntry, JourneysFeedResponse, MovePlacementEnum } from "../../../api/sdk";

/** Where a journey moves: next to a neighbour, before or after it, and into its year. */
export interface MoveTarget {
  neighborJourneyId: string;
  placement: MovePlacementEnum;
  traveledYear: number;
}

/**
 * Turns "a row was dropped onto another's place" into a move request, or `null` if the row
 * stayed in place.
 *
 * Dragged down, the journey lands after the one it was dropped on; up, before it. The year comes
 * from the neighbour. So to reach the end of a year a row is brought from above, and the start of
 * a year from below.
 */
export function resolveMoveTarget(
  journeys: readonly JourneyFeedEntry[],
  activeId: string,
  overId: string,
): MoveTarget | null {
  const from = journeys.findIndex((journey) => journey.journeyId === activeId);
  const to = journeys.findIndex((journey) => journey.journeyId === overId);
  if (from === -1 || to === -1 || from === to) {
    return null;
  }

  const neighbor = journeys[to];
  return {
    neighborJourneyId: neighbor.journeyId,
    placement: to > from ? "after" : "before",
    traveledYear: neighbor.traveledYear,
  };
}

/**
 * Offset of feed rows while a row is carried: rows between its place and the target yield exactly
 * its height. Rows within a year are flush, while the standard dnd-kit strategy adds the distance
 * to the neighbouring row to the height; at a year boundary that includes the heading, and the
 * row visually ended up in the wrong year. `yearHeaderShift` shifts headings by the same height.
 */
export const feedSortingStrategy: SortingStrategy = ({ activeIndex, activeNodeRect, index, rects, overIndex }) => {
  const height = (rects[activeIndex] ?? activeNodeRect)?.height;
  if (height === undefined || index === activeIndex) {
    return null;
  }

  let y = 0;
  if (index > activeIndex && index <= overIndex) {
    y = -height;
  } else if (index < activeIndex && index >= overIndex) {
    y = height;
  }

  return y === 0 ? null : { x: 0, y, scaleX: 1, scaleY: 1 };
};

/**
 * Offset (px, vertical) of a year heading while a row is carried; pairs with `feedSortingStrategy`.
 *
 * A heading sits before the first row of its year. If it falls between the row's place and the
 * target, it yields the row's height along with the rows: the screen then shows which year the
 * row will land in, and rows under the target stay in their year.
 *
 * `activeIndex` is the dragged row's place in the feed, `overIndex` the row it is held over,
 * `firstRowIndex` the first row of this heading's year, `height` the dragged row's height in px.
 */
export function yearHeaderShift({
  activeIndex,
  overIndex,
  firstRowIndex,
  height,
}: {
  activeIndex: number;
  overIndex: number;
  firstRowIndex: number;
  height: number;
}): number {
  if (activeIndex === -1 || overIndex === -1) {
    return 0;
  }

  if (activeIndex < firstRowIndex && firstRowIndex <= overIndex) {
    return -height;
  }

  if (overIndex < firstRowIndex && firstRowIndex <= activeIndex) {
    return height;
  }

  return 0;
}

/**
 * Reorders a journey in the loaded feed pages, the same way the backend will.
 *
 * The journey lands next to its neighbour in its page and takes its year. If the neighbour or the
 * journey is not in the pages, the pages are returned unchanged. Returns new pages.
 */
export function moveJourneyInPages(
  pages: readonly JourneysFeedResponse[],
  journeyId: string,
  target: MoveTarget,
): JourneysFeedResponse[] {
  const moved = pages.flatMap((page) => page.items).find((journey) => journey.journeyId === journeyId);
  const hasNeighbor = pages.some((page) => page.items.some((journey) => journey.journeyId === target.neighborJourneyId));
  if (!moved || !hasNeighbor) {
    return [...pages];
  }

  const placed: JourneyFeedEntry = { ...moved, traveledYear: target.traveledYear };
  return pages.map((page) => {
    const items = page.items.filter((journey) => journey.journeyId !== journeyId);
    const neighborIndex = items.findIndex((journey) => journey.journeyId === target.neighborJourneyId);
    if (neighborIndex === -1) {
      return { ...page, items };
    }

    const insertAt = target.placement === "after" ? neighborIndex + 1 : neighborIndex;
    return { ...page, items: [...items.slice(0, insertAt), placed, ...items.slice(insertAt)] };
  });
}

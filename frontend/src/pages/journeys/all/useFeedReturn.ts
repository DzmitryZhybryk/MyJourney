import { useLayoutEffect, useRef, type RefObject } from "react";

/**
 * Keeps the feed's place while the journey card covers it: the scroll position, and on return
 * focus on the row of the journey just closed (the feed itself if the row is gone, e.g. its year
 * left the filter).
 *
 * The scroller is the feed card on desktop and the window on narrow screens. A hidden feed
 * (`display: none`) loses its `scrollTop`, so the position is recorded while the feed is shown.
 * Focus does not scroll, or it would undo the restored position.
 */
export function useFeedReturn(
  feedRef: RefObject<HTMLElement | null>,
  cardJourneyId: string | null,
  isDesktop: boolean,
): void {
  const scrollTop = useRef(0);
  const closingId = useRef<string | null>(null);
  const isFeedShown = cardJourneyId === null;

  useLayoutEffect(() => {
    if (cardJourneyId !== null) {
      closingId.current = cardJourneyId;
      return;
    }

    const feed = feedRef.current;
    const closedId = closingId.current;
    if (!feed || closedId === null) {
      return;
    }

    closingId.current = null;
    if (isDesktop) {
      feed.scrollTop = scrollTop.current;
    } else {
      window.scrollTo(0, scrollTop.current);
    }
    const row = Array.from(feed.querySelectorAll<HTMLElement>("[data-flip-id]")).find(
      (element) => element.dataset.flipId === closedId,
    );
    (row?.querySelector<HTMLElement>("a") ?? feed).focus({ preventScroll: true });
  }, [cardJourneyId, feedRef, isDesktop]);

  useLayoutEffect(() => {
    const feed = feedRef.current;
    if (!feed || !isFeedShown) {
      return;
    }

    const record = () => {
      scrollTop.current = isDesktop ? feed.scrollTop : window.scrollY;
    };
    const scroller = isDesktop ? feed : window;
    scroller.addEventListener("scroll", record, { passive: true });

    return () => scroller.removeEventListener("scroll", record);
  }, [feedRef, isFeedShown, isDesktop]);
}

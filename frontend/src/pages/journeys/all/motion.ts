import { useEffect, useLayoutEffect, useRef, useState, type RefObject } from "react";

import { prefersReducedMotion } from "../../../components/reducedMotion";

const ODOMETER_MS = 600;
const FLIP_MS = 260;

/**
 * A number that rolls to a new value like an odometer when it changes; returns the currently
 * displayed value.
 *
 * The first value shows immediately; only changes animate (e.g. the distance after editing a journey).
 */
export function useAnimatedNumber(value: number): number {
  const [shown, setShown] = useState(value);
  const shownRef = useRef(value);
  const isReduced = prefersReducedMotion();

  useEffect(() => {
    const from = shownRef.current;
    if (from === value) {
      return;
    }

    if (isReduced) {
      shownRef.current = value;
      return;
    }

    let frame = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const progress = Math.min((now - start) / ODOMETER_MS, 1);
      // Ease out: the last digits roll slower.
      const eased = 1 - (1 - progress) ** 3;
      shownRef.current = from + (value - from) * eased;
      setShown(shownRef.current);
      if (progress < 1) {
        frame = requestAnimationFrame(tick);
      }
    };
    frame = requestAnimationFrame(tick);

    return () => cancelAnimationFrame(frame);
  }, [value, isReduced]);

  return isReduced ? value : shown;
}

/**
 * FLIP list animation: elements with `data-flip-id` that changed place after a render glide from
 * the old place to the new one, and new ones fade in.
 *
 * Positions are measured after every render, so the animation fires on any reorder: a filter, a
 * move, an edit with another year. While `isPaused` (a drag is in progress and dnd-kit moves the
 * rows) it only measures. While `isHidden` (the list sits under `display: none`) it forgets the
 * positions, so the first render after showing again only measures. Elements must be positioned
 * relative to the container.
 */
export function useFlip(containerRef: RefObject<HTMLElement | null>, isPaused: boolean, isHidden = false): void {
  // Position is `offsetTop` within the feed, not the on-screen position: scrolling does not change it.
  const tops = useRef(new Map<string, number>());

  // No dependency array: measuring is needed after every render, and there is always something to compare against.
  useLayoutEffect(() => {
    const container = containerRef.current;
    // Hidden rows have no layout and report `offsetTop` 0: comparing against that would fly every row in.
    if (isHidden) {
      tops.current = new Map();
      return;
    }
    if (!container) {
      return;
    }

    const isAnimated = !isPaused && !prefersReducedMotion();
    const next = new Map<string, number>();
    for (const element of container.querySelectorAll<HTMLElement>("[data-flip-id]")) {
      const id = element.dataset.flipId ?? "";
      const top = element.offsetTop;
      next.set(id, top);

      // jsdom and old browsers without Web Animations: no animation.
      if (!isAnimated || typeof element.animate !== "function") {
        continue;
      }

      const previous = tops.current.get(id);
      if (previous === undefined) {
        if (tops.current.size > 0) {
          element.animate([{ opacity: 0 }, { opacity: 1 }], { duration: FLIP_MS, easing: "ease-out" });
        }
        continue;
      }

      const deltaY = previous - top;
      if (Math.abs(deltaY) >= 1) {
        element.animate([{ transform: `translateY(${deltaY}px)` }, { transform: "translateY(0)" }], {
          duration: FLIP_MS,
          easing: "ease-out",
        });
      }
    }

    tops.current = next;
  });
}

import { useEffect, useRef, useState } from "react";

interface YearHeaderProps {
  id: string;
  year: number;
  /** Vertical offset, px, while a row is carried across this year. */
  shift: number;
}

/** Nearest scrollable ancestor; `null` means the page itself scrolls. */
function scrollParentOf(element: HTMLElement): HTMLElement | null {
  for (let parent = element.parentElement; parent; parent = parent.parentElement) {
    const { overflowY } = getComputedStyle(parent);
    if (overflowY === "auto" || overflowY === "scroll") {
      return parent;
    }
  }

  return null;
}

/**
 * Year heading in the feed; sticks to the top while its journeys are on screen.
 *
 * Only a stuck heading has a background, since rows scroll under it. Otherwise it is transparent
 * like the rows, or the feed would read as a zebra. A stuck heading sits one pixel above the
 * scroll edge (`top: -1px`), so the observer sees it as not fully visible.
 */
export function YearHeader({ id, year, shift }: YearHeaderProps) {
  const ref = useRef<HTMLHeadingElement>(null);
  const [isStuck, setIsStuck] = useState(false);
  useEffect(() => {
    const header = ref.current;
    /* v8 ignore next 3 -- the heading renders together with the effect */
    if (!header) {
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) =>
        setIsStuck(
          entry.intersectionRatio < 1 && entry.rootBounds !== null && entry.boundingClientRect.top < entry.rootBounds.top,
        ),
      { root: scrollParentOf(header), threshold: [1] },
    );
    observer.observe(header);
    return () => observer.disconnect();
  }, []);

  return (
    <h2
      ref={ref}
      id={id}
      className="year-header"
      data-stuck={isStuck || undefined}
      style={shift === 0 ? undefined : { transform: `translateY(${shift}px)` }}
    >
      {year}
    </h2>
  );
}

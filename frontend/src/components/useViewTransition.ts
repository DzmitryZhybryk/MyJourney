import { useEffect, useLayoutEffect, useRef, useState } from "react";

import { prefersReducedMotion } from "./reducedMotion";
import { isSameView, type ViewBox } from "./worldProjection";

const TRANSITION_MS = 600;

/**
 * One flight to whatever the target is while it lasts (a new object is a new flight). It starts at
 * `from` and reads the target every frame, so a target that arrives a render later is still the
 * destination. `isAnimated: false` (or reduced motion) lands on the target at the first frame.
 */
export interface ViewFlight {
  from: ViewBox;
  isAnimated: boolean;
}

// Ease in-out cubic.
function ease(progress: number): number {
  return progress < 0.5 ? 4 * progress ** 3 : 1 - (-2 * progress + 2) ** 3 / 2;
}

function interpolate(from: ViewBox, to: ViewBox, eased: number): ViewBox {
  return {
    x: from.x + (to.x - from.x) * eased,
    y: from.y + (to.y - from.y) * eased,
    width: from.width + (to.width - from.width) * eased,
    height: from.height + (to.height - from.height) * eased,
  };
}

/**
 * Eases the map's visible area to a new target instead of jumping (`isEnabled`), and plays
 * `flight` when one is given.
 *
 * A new target mid-transition continues from the view currently on screen; a target equal by value
 * to the current one changes nothing. While a flight runs, target changes join it instead of
 * starting their own transition. With reduced motion, or when disabled, the view changes
 * immediately. Returns the view for the current frame.
 */
export function useViewTransition(target: ViewBox, isEnabled: boolean, flight: ViewFlight | null = null): ViewBox {
  const [shown, setShown] = useState(target);
  const shownRef = useRef(target);
  const targetRef = useRef(target);
  const isAnimated = isEnabled && !prefersReducedMotion();

  // The flight shows its start view from the very render it arrives in, not one frame later.
  const [trackedFlight, setTrackedFlight] = useState(flight);
  const [isFlying, setIsFlying] = useState(false);
  if (flight !== trackedFlight) {
    setTrackedFlight(flight);
    setIsFlying(flight !== null);
    if (flight !== null) {
      setShown(flight.from);
    }
  }

  // Before any rAF tick, so the first frame of a flight already sees the latest target.
  useLayoutEffect(() => {
    targetRef.current = target;
  });

  useEffect(() => {
    if (flight === null) {
      return;
    }

    shownRef.current = flight.from;
    const duration = flight.isAnimated && !prefersReducedMotion() ? TRANSITION_MS : 0;
    let frame = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const progress = duration === 0 ? 1 : Math.min((now - start) / duration, 1);
      const next = progress === 1 ? targetRef.current : interpolate(flight.from, targetRef.current, ease(progress));
      shownRef.current = next;
      setShown(next);
      if (progress < 1) {
        frame = requestAnimationFrame(tick);
      } else {
        setIsFlying(false);
      }
    };
    frame = requestAnimationFrame(tick);

    return () => cancelAnimationFrame(frame);
  }, [flight]);

  useEffect(() => {
    if (isFlying) {
      return;
    }

    if (!isAnimated) {
      shownRef.current = target;
      return;
    }

    const from = shownRef.current;
    if (isSameView(from, target)) {
      return;
    }

    let frame = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const progress = Math.min((now - start) / TRANSITION_MS, 1);
      const next = progress === 1 ? target : interpolate(from, target, ease(progress));
      shownRef.current = next;
      setShown(next);
      if (progress < 1) {
        frame = requestAnimationFrame(tick);
      }
    };
    frame = requestAnimationFrame(tick);

    return () => cancelAnimationFrame(frame);
  }, [target, isAnimated, isFlying]);

  return isFlying || isAnimated ? shown : target;
}

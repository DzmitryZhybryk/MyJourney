import { Suspense, useEffect, useState, type ReactNode } from "react";
import { useLocation, useOutlet } from "react-router";

import "./public-crossfade.css";

/** Fade delay + duration; must match `public-crossfade.css`. */
const FADE_DELAY_MS = 300;
const FADE_DURATION_MS = 550;

interface LeavingScreen {
  pathname: string;
  node: ReactNode;
  /** Scroll position at the moment of leaving; see `top` in `public-crossfade.css`. */
  scrollY: number;
}

/**
 * Cross-fade between public zone screens: landing <-> signup <-> login.
 *
 * Public screens are different ROUTES and React removes the old page in the same frame, so the
 * switch would read as a jerk. The wrapper keeps the old page mounted for the fade length and
 * fades it out over the incoming one: both fades run simultaneously with the same delay.
 *
 * The wrapper key is the path and both slots have the same structure (`div > Suspense > node`):
 * by key React recognizes a node that moved from the active slot to the leaving one and reuses it
 * instead of remounting. Otherwise a fresh copy of the page would fade out, with a reset form and
 * mount effects rerun.
 *
 * `Suspense` is OWN here, not the shared one from `App`: child pages are lazy, and with a single
 * Suspense above `<Routes>` loading a neighbouring screen's chunk would unmount the whole layout
 * with the globe: WebGL would be recreated and the camera would snap to the new face without a
 * flight. A separate boundary per screen is needed for the same reason: an incoming screen stuck
 * loading must not fade out the leaving one.
 */
export function PublicCrossfade() {
  const { pathname } = useLocation();
  const outlet = useOutlet();
  const [shownPath, setShownPath] = useState(pathname);
  const [leaving, setLeaving] = useState<LeavingScreen | null>(null);
  // Node of the PREVIOUS render: updated below right in render (not in an effect). React does not
  // guarantee reading a ref during render, while state adjusted the same way as shownPath/leaving
  // above gives the same "one render behind" safely.
  const [previousNode, setPreviousNode] = useState<ReactNode>(outlet);

  if (shownPath !== pathname) {
    setLeaving({
      pathname: shownPath,
      node: previousNode,
      // Read scroll here, before commit: afterwards the document shrinks to the incoming screen
      // and the browser clamps the scroll position, losing where the user was.
      scrollY: window.scrollY,
    });
    setShownPath(pathname);
  }

  if (previousNode !== outlet) {
    setPreviousNode(outlet);
  }

  useEffect(() => {
    if (leaving === null) return;

    const timer = window.setTimeout(() => setLeaving(null), FADE_DELAY_MS + FADE_DURATION_MS);
    return () => window.clearTimeout(timer);
  }, [leaving]);

  return (
    <>
      {leaving !== null && (
        <div
          key={leaving.pathname}
          className="public-crossfade__screen public-crossfade__screen--leaving"
          style={{ top: -leaving.scrollY }}
          inert
        >
          <Suspense fallback={null}>{leaving.node}</Suspense>
        </div>
      )}
      <div
        key={pathname}
        className={
          leaving === null
            ? "public-crossfade__screen"
            : "public-crossfade__screen public-crossfade__screen--entering"
        }
      >
        <Suspense fallback={null}>{outlet}</Suspense>
      </div>
    </>
  );
}

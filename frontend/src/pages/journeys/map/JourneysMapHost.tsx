import { lazy, Suspense, useEffect, useState } from "react";
import { useLocation } from "react-router";

import { prefersReducedMotion } from "../../../components/reducedMotion";
import type { WorldMapLayer } from "../../../components/WorldMap";
import { useJourneysMapScene, type JourneysMapScene } from "./journeysMapScene";

/*
 * The map itself (country borders) is a separate chunk: /journeys/add opened directly never loads
 * it. The map tabs import the same module statically, so on their routes it arrives with the tab.
 */
const JourneysSharedMap = lazy(() => import("./JourneysSharedMap").then((m) => ({ default: m.JourneysSharedMap })));

// How long the previous tab's layer stays: its fade-out, `--map-leave` in world-map.css.
const LEAVE_MS = 240;

// Routes whose tab draws on the shared map; on the rest (wishlist, add) the map is hidden.
const MAP_ROUTES: ReadonlySet<string> = new Set(["/journeys", "/journeys/movements", "/journeys/all"]);
// The feed's journey card (/journeys/all/<id>) is the same tab and draws the journey's arc.
const JOURNEY_CARD_PREFIX = "/journeys/all/";

function isMapRoute(pathname: string): boolean {
  const path = pathname.replace(/\/+$/u, "");
  return MAP_ROUTES.has(path) || path.startsWith(JOURNEY_CARD_PREFIX);
}

/**
 * Slot of the shared Journeys map in the section shell. Mounts the map once the first tab
 * publishes a scene and keeps it mounted afterwards: leaving for a screen without a map hides it,
 * coming back shows the same instance. While hidden, the last published scene stays drawn.
 *
 * Moving between two map tabs flies the frame. Coming back from a screen without a map counts as
 * a new scene even for the same tab: the user's zoom is dropped and the map appears straight on
 * the tab's frame, since a flight under a fade-in would only be seen half-way.
 */
export function JourneysMapHost() {
  const { pathname } = useLocation();
  const scene = useJourneysMapScene();
  const isOnMapRoute = isMapRoute(pathname);
  const [reducedMotion] = useState(prefersReducedMotion);

  // Decided on navigation, not on the scene: the new tab's scene arrives a render after its route,
  // so `scene` here is still the previous screen's one (`null` for the feed on a narrow screen).
  const [trackedPathname, setTrackedPathname] = useState(pathname);
  const [isFlightAllowed, setIsFlightAllowed] = useState(false);
  const [visit, setVisit] = useState(0);
  if (pathname !== trackedPathname) {
    const wasMapShown = isMapRoute(trackedPathname) && scene !== null;
    setTrackedPathname(pathname);
    setIsFlightAllowed(wasMapShown && isOnMapRoute);
    if (!wasMapShown && isOnMapRoute) {
      setVisit((current) => current + 1);
    }
  }

  // The previous tab's dots and arcs fade out while the frame flies to the new tab.
  const [shownScene, setShownScene] = useState<JourneysMapScene | null>(scene);
  const [leaving, setLeaving] = useState<WorldMapLayer | null>(null);
  if (scene !== null && scene !== shownScene) {
    setShownScene(scene);
    if (shownScene !== null && shownScene.tabId !== scene.tabId && isFlightAllowed && !reducedMotion) {
      setLeaving({ key: shownScene.tabId, countries: shownScene.countries, overlay: shownScene.overlay });
    }
  }

  useEffect(() => {
    if (leaving === null) return;

    const timer = window.setTimeout(() => setLeaving(null), LEAVE_MS);
    return () => window.clearTimeout(timer);
  }, [leaving]);

  if (shownScene === null) {
    return null;
  }

  return (
    <Suspense fallback={null}>
      <JourneysSharedMap
        scene={shownScene}
        sceneKey={`${shownScene.tabId}#${visit}`}
        isSceneChangeAnimated={isFlightAllowed}
        isVisible={scene !== null && isOnMapRoute}
        leaving={leaving}
      />
    </Suspense>
  );
}

import { useQuery } from "@tanstack/react-query";
import { lazy, Suspense, useEffect, useMemo, useState, type CSSProperties } from "react";
import { useTranslation } from "react-i18next";
import { useLocation } from "react-router";

import { cityLabel, useCityNames } from "../../api/cityNames";
import { getJourneysGlobeOptions } from "../../api/sdk";
import { useAuth } from "../../auth/useAuth";
import { ErrorBoundary } from "../ErrorBoundary";
import { prefersReducedMotion } from "../reducedMotion";
import type { GlobePov } from "./GlobeCanvas";
import { useGlobeScene, type GlobeSlot } from "./globeScene";
import { CAMERA_MAX_ALTITUDE, isRealCity, ROUTE_FADE_MS, routeCameraPov, type GlobeRoute } from "./route";
import { ROUTE_ARCS, ROUTE_CITIES, type GlobeCity } from "./routes";
import { citiesFromJourneysGlobe, type UserCityPoint } from "./userCities";
import "./persistent-globe.css";

/*
 * The canvas is lazy, in its own chunk: three/react-globe.gl (~1.8 MB) must stay off the
 * first-paint critical path of EVERY screen. The wrapper below (dark backdrop + framing by
 * data-screen) is pure CSS and appears in the first frame without WebGL, hence `fallback={null}`.
 */
const GlobeCanvas = lazy(() => import("./GlobeCanvas").then((m) => ({ default: m.GlobeCanvas })));

/**
 * A globe "screen": a camera face plus sphere framing (`data-screen`). Public faces
 * (landing/signup/login), authenticated `home`, and `journeyAdd` (the journey form column, framed
 * by the slot the page publishes). Other `/journeys*` routes have no face: the globe hides there
 * (`visible=false`), staying on the last one.
 */
type Screen = "landing" | "signup" | "login" | "home" | "journeyAdd";

// Stable "no points" reference: `react-globe.gl` compares layer data by identity, and a new `[]`
// each render would make it rebuild the label layer for nothing.
const NO_CITIES: readonly GlobeCity[] = [];
const NO_USER_CITIES: readonly UserCityPoint[] = [];

// Camera point of view per face: different sides of the planet so a transition reads as a
// fly-over. `home` is the dashboard face, separate from login, so login -> home is a visible
// camera flight.
const SCREEN_POV: Record<Screen, GlobePov> = {
  landing: { lat: 22, lng: 24, altitude: 2.35 },
  signup: { lat: 44, lng: -34, altitude: 1.85 },
  login: { lat: 8, lng: 104, altitude: 1.95 },
  home: { lat: 25, lng: 20, altitude: CAMERA_MAX_ALTITUDE },
  journeyAdd: routeCameraPov(null),
};

interface GlobeView {
  screen: Screen;
  pov: GlobePov;
  autoRotate: boolean;
  /** Drag rotation by cursor/finger. On only where the planet is the screen's main object. */
  interactive: boolean;
  /** Whether the globe background is visible. `false` on `/journeys*`, where a 2D map/form takes its place. */
  visible: boolean;
}

/**
 * Picks the face, rotation mode, interactivity and visibility for the current path.
 *
 * `/journeys/add` with a published slot is the `journeyAdd` face (planet in the form column,
 * hand-rotatable). While no city is picked in the form it spins as on the dashboard; with the
 * first city it stops: the camera frames the route and spinning would carry it out of frame.
 * Without a slot (narrow screen: column hidden) and on other `/journeys*` routes (2D `WorldMap`)
 * the globe is hidden. On auth forms (login/signup) the planet rests as a calm background;
 * landing and dashboard spin. Drag rotation is on the dashboard and journey form: on other faces
 * the globe is purely decorative and the layer keeps `pointer-events: none` (see persistent-globe.css).
 */
function viewForPath(pathname: string, hasSlot: boolean, hasRouteCity: boolean): GlobeView {
  if (pathname.startsWith("/journeys/add") && hasSlot) {
    return {
      screen: "journeyAdd",
      pov: SCREEN_POV.journeyAdd,
      autoRotate: !hasRouteCity,
      interactive: true,
      visible: true,
    };
  }

  if (pathname.startsWith("/journeys")) {
    // Hidden and paused: no rotation needed (a guard in case the pause has not landed yet).
    return { screen: "home", pov: SCREEN_POV.home, autoRotate: false, interactive: false, visible: false };
  }

  if (pathname.startsWith("/home")) {
    return { screen: "home", pov: SCREEN_POV.home, autoRotate: true, interactive: true, visible: true };
  }

  if (pathname.startsWith("/signup")) {
    return { screen: "signup", pov: SCREEN_POV.signup, autoRotate: false, interactive: false, visible: true };
  }

  if (pathname.startsWith("/login")) {
    return { screen: "login", pov: SCREEN_POV.login, autoRotate: false, interactive: false, visible: true };
  }

  return { screen: "landing", pov: SCREEN_POV.landing, autoRotate: true, interactive: false, visible: true };
}

/**
 * CSS variables for framing the `journeyAdd` face: the viewport-sized canvas is only moved so its
 * center lands on the slot center; its scale equals the dashboard's (see persistent-globe.css),
 * so leaving for /home moves the sphere rather than resizing it. The clip limits the canvas to
 * the slot rectangle, otherwise at close zoom the texture would show through the form glass.
 */
function slotFramingStyle(slot: GlobeSlot): CSSProperties {
  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;
  const offsetX = slot.left + slot.width / 2 - viewportWidth / 2;
  const offsetY = slot.top + slot.height / 2 - viewportHeight / 2;
  const right = viewportWidth - (slot.left + slot.width);
  const bottom = viewportHeight - (slot.top + slot.height);

  return {
    "--globe-slot-x": `${offsetX}px`,
    "--globe-slot-y": `${offsetY}px`,
    "--globe-slot-clip": `inset(${slot.top}px ${right}px ${bottom}px ${slot.left}px)`,
  } as CSSProperties;
}

/**
 * App-global persistent globe background. Mounted once at the root (sibling of `<Routes>`) and
 * NOT unmounted by any navigation: the camera flies between faces (`pov`) and the WebGL instance
 * lives continuously, including `/login` -> `/home` after login.
 *
 * The point source depends on auth: anonymous users see curated routes (`ROUTE_ARCS` /
 * `ROUTE_CITIES`), logged-in ones their own real visited cities without arcs. The real cities
 * come from the same request as the 2D map (`/v1/journeys/map/`); Query owns the cache and its
 * reset on session change (see `AuthProvider`).
 */
export function PersistentGlobeHost() {
  const { pathname } = useLocation();
  const { isAuthenticated } = useAuth();
  const { route, slot } = useGlobeScene();
  const hasRouteCity = isRealCity(route?.origin ?? null) || isRealCity(route?.destination ?? null);
  const view = viewForPath(pathname, slot !== null, hasRouteCity);
  const isJourneyAdd = view.screen === "journeyAdd";
  // On the form face the camera frames the route; GlobeCanvas compares pov by fields, not by reference.
  const pov = isJourneyAdd ? routeCameraPov(route) : view.pov;
  const [reducedMotion] = useState(prefersReducedMotion);

  /*
   * Leaving the form for the dashboard: the route does not vanish but fades while the camera and
   * frame fly to the home face. The transition is caught by the face change right in render (not
   * an effect, otherwise one home frame would pass without the route): in this render the scene
   * still holds the form route, the page clears it in its unmount cleanup afterwards. Only on
   * /home: logging out or going to the 2D map does not keep the route (on login it would lie
   * over the curated arcs).
   */
  const [previousScreen, setPreviousScreen] = useState<Screen>(view.screen);
  const [fadingRoute, setFadingRoute] = useState<GlobeRoute | null>(null);
  if (previousScreen !== view.screen) {
    setPreviousScreen(view.screen);
    const isLeavingToHome = previousScreen === "journeyAdd" && view.screen === "home" && view.visible;
    setFadingRoute(isLeavingToHome && !reducedMotion ? route : null);
  }

  useEffect(() => {
    if (fadingRoute === null) return;

    const timer = window.setTimeout(() => setFadingRoute(null), ROUTE_FADE_MS);
    return () => window.clearTimeout(timer);
  }, [fadingRoute]);

  let canvasRoute: GlobeRoute | null = null;
  if (isJourneyAdd) {
    canvasRoute = route;
  } else if (fadingRoute !== null) {
    canvasRoute = fadingRoute;
  }

  // The background does not refresh the snapshot: a new journey arrives via invalidation from the
  // form, not a refetch on mount. Errors are deliberately ignored: without points the globe is still a globe.
  const { data: userCityPoints = NO_USER_CITIES } = useQuery({
    ...getJourneysGlobeOptions(),
    enabled: isAuthenticated,
    staleTime: Infinity,
    select: citiesFromJourneysGlobe,
  });

  // City names use the same request and cache as the 2D map. A city whose name is still loading
  // or failed to arrive is a dot without a label; a city geo does not know is labelled as unknown.
  const { t } = useTranslation("common");
  const unknownLabel = t("map.unknownCity");
  const nameOf = useCityNames(userCityPoints.map((city) => city.id));
  const userCities = useMemo(() => {
    const cities: readonly GlobeCity[] = userCityPoints.map((city) => ({
      name: cityLabel(nameOf(city.id), unknownLabel),
      lat: city.lat,
      lng: city.lng,
    }));

    return cities.length > 0 ? cities : NO_CITIES;
  }, [userCityPoints, nameOf, unknownLabel]);

  // Curated guest cities are labelled in the UI language; `t` changes with the language.
  const routeCities = useMemo<readonly GlobeCity[]>(
    () => ROUTE_CITIES.map((city) => ({ name: t(`globe.cities.${city.id}`), lat: city.lat, lng: city.lng })),
    [t],
  );

  // On the form face only the route is drawn, not visited cities.
  let labelCities = isAuthenticated ? userCities : routeCities;
  if (isJourneyAdd) {
    labelCities = NO_CITIES;
  }

  return (
    <div
      className="persistent-globe"
      data-screen={view.screen}
      data-visible={view.visible}
      data-interactive={view.interactive}
      style={isJourneyAdd && slot !== null ? slotFramingStyle(slot) : undefined}
      aria-hidden
    >
      {/*
       * Clip lives on a separate NON-transformed wrapper: a clip-path on the stage would be
       * computed in its local (scaled) coordinates, and on the host itself it would cut its night too.
       */}
      <div className="persistent-globe__clip">
        {/* Sphere framing (shift/scale) is set by CSS per data-screen. */}
        <div className="persistent-globe__stage">
          {/*
           * Boundary right around the canvas: a WebGL/three.js (or GlobeCanvas chunk) failure drops
           * only the sphere, while the host's CSS layer (night gradient, data-screen framing and
           * the auth form scrim) lives without WebGL. No fallback needed: the host holds the backdrop.
           */}
          <ErrorBoundary fallback={null}>
            <Suspense fallback={null}>
              <GlobeCanvas
                arcs={isAuthenticated ? undefined : ROUTE_ARCS}
                labelCities={labelCities}
                route={canvasRoute}
                routeFading={!isJourneyAdd && fadingRoute !== null}
                pov={pov}
                // On the form face the globe appears with a fly-in to the planet, not just a fade.
                reveal={isJourneyAdd}
                autoRotate={view.autoRotate}
                interactive={view.interactive}
                paused={!view.visible}
              />
            </Suspense>
          </ErrorBoundary>
        </div>
      </div>

      {/* Side scrim behind the form (auth screens); transparent on landing/dashboard. */}
      <div className="persistent-globe__scrim" />
    </div>
  );
}

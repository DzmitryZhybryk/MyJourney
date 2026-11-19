import { useEffect, useRef, useState } from "react";
import Globe, { type GlobeMethods } from "react-globe.gl";

import { prefersReducedMotion } from "../reducedMotion";
import { revealPov } from "./cameraReveal";
import { GLOBE_ATMOSPHERE_COLOR, GLOBE_BUMP_URL, GLOBE_TEXTURE_URL } from "./constants";
import { applyLabelDeclutter, applyLabelVisibility, createGlobeLabel } from "./globeLabel";
import { type LabelBox, resolveLabelVisibility } from "./labelDeclutter";
import type { GlobeRoute, TrailPoint } from "./route";
import {
  applyRouteVisibility,
  createRouteElement,
  isRouteDatum,
  isRouteElement,
  useRouteScene,
  type RouteTrail,
} from "./routeScene";
import type { GlobeCity, RouteArc } from "./routes";
import { hitsSphere, useGlobeZoom } from "./useGlobeZoom";
import "./globe-label.css";
import "./globe-canvas.css";

export interface GlobePov {
  lat: number;
  lng: number;
  altitude: number;
}

/*
 * Only props that a consumer actually passes; do not add speculative options (an unused option
 * is a setting someone must not break).
 */
interface GlobeCanvasProps {
  /** Route arcs (`arcsData`); none by default. */
  arcs?: readonly RouteArc[];
  /** End cities for labels (dot + name with occlusion); none by default. */
  labelCities?: readonly GlobeCity[];
  /** Auto-rotation (disabled under prefers-reduced-motion). */
  autoRotate?: boolean;
  /** Camera point of view. The first set is instant, later changes fly smoothly. */
  pov?: GlobePov;
  /** Hidden by the route (e.g. `/journeys`): rendering is paused so WebGL does not spin idle. */
  paused?: boolean;
  /**
   * Drag rotation on both axes and pinch zoom. Gestures are hit-tested pixel-wise on the sphere
   * itself; off the sphere they go to the page.
   */
  interactive?: boolean;
  /** Journey form route: end pins, trail and moving vehicle; none by default. */
  route?: GlobeRoute | null;
  /** The route is fading (leaving the journey form for the dashboard); the host then removes it. */
  routeFading?: boolean;
  /**
   * Appearance (first set or leaving pause) as a camera fly-in with extra spin that hands over to
   * auto-rotation (see cameraReveal.ts). Without it the camera snaps to `pov`.
   */
  reveal?: boolean;
}

const DEFAULT_POV: GlobePov = { lat: 22, lng: 24, altitude: 2.3 };
/** Minimum label declutter recompute interval: the fade lasts 0.4s, so more often only costs layout reads. */
const DECLUTTER_INTERVAL_MS = 150;
/** Auto-rotation speed, shared by all globes. */
const AUTO_ROTATE_SPEED = 0.42;
// The same speed in degrees of camera longitude per second: OrbitControls rotates 2π/60·speed rad/s
// and its `_rotateLeft` decreases the azimuth, which in three-globe is the camera longitude.
const AUTO_ROTATE_DEG_PER_SEC = -6 * AUTO_ROTATE_SPEED;
const POV_FLIGHT_MS = 1400;
const ARC_COLOR: [string, string] = ["rgba(246, 177, 122, 0.95)", "rgba(111, 143, 214, 0.55)"];
// Stable empty references so defaults do not recreate arrays every render.
const EMPTY_ARCS: readonly RouteArc[] = [];
const EMPTY_CITIES: readonly GlobeCity[] = [];

/*
 * Accessors are module constants, NOT arrows in JSX. globe.gl compares accessors by identity: a
 * new function each render reads as "the drawing rule changed" and the layer is rebuilt entirely.
 * For `htmlElement` that means tearing down and rebuilding the DOM of all labels for nothing,
 * just because the parent rerendered (it does on every route change: `PersistentGlobeHost`
 * uses `useLocation`).
 */
const arcColorAccessor = (): [string, string] => ARC_COLOR;
const arcDashInitialGapAccessor = (d: object): number => (d as RouteArc).dashInitialGap;
/*
 * globe.gl has a single html layer, so city labels and route elements (pins, vehicle) share it:
 * accessors tell datums apart by the route's `kind` discriminator.
 */
const htmlLatAccessor = (d: object): number => (d as GlobeCity | { lat: number }).lat;
const htmlLngAccessor = (d: object): number => (d as GlobeCity | { lng: number }).lng;
const htmlAltitudeAccessor = (d: object): number => (isRouteDatum(d) ? d.alt : 0);
const htmlElementAccessor = (d: object): HTMLElement => {
  if (isRouteDatum(d)) {
    return createRouteElement(d);
  }

  const city = d as GlobeCity;
  return createGlobeLabel(city.name, `${city.name ?? ""}|${city.lat}|${city.lng}`);
};
// Far-side occlusion: labels fade via opacity, the route hides instantly.
const htmlVisibilityModifier = (el: HTMLElement, isVisible: boolean): void => {
  if (isRouteElement(el)) {
    applyRouteVisibility(el, isVisible);
    return;
  }

  applyLabelVisibility(el, isVisible);
};
// react-globe.gl types its data props and `pathPoints` as mutable arrays but only reads them,
// so readonly arrays are passed through with a cast.
const pathPointsAccessor = (d: object): TrailPoint[] => (d as RouteTrail).coords as TrailPoint[];
const pathPointLatAccessor = (p: unknown): number => (p as TrailPoint).lat;
const pathPointLngAccessor = (p: unknown): number => (p as TrailPoint).lng;
const pathPointAltAccessor = (p: unknown): number => (p as TrailPoint).alt;
const pathColorAccessor = (d: object): string => (d as RouteTrail).color;

/**
 * Shared base of the decorative 3D globe (the product's signature). Encapsulates container
 * measuring, warm tint, atmosphere, reduced motion, auto-rotation, camera flights (pov) and
 * optional drag rotation and pinch zoom on the sphere. Optionally draws route arcs, end-city
 * labels (HTML labels with far-side occlusion) and the journey form route (pins, trail, moving
 * vehicle, see routeScene.ts). Consumer: the app-global globe background (`PersistentGlobeHost`).
 */
export function GlobeCanvas({
  arcs = EMPTY_ARCS,
  labelCities = EMPTY_CITIES,
  autoRotate = true,
  pov = DEFAULT_POV,
  paused = false,
  interactive = false,
  route = null,
  routeFading = false,
  reveal = false,
}: GlobeCanvasProps) {
  const globeRef = useRef<GlobeMethods | undefined>(undefined);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const hasSetPovRef = useRef(false);
  // `paused` of the previous commit: the camera effect reads it BEFORE the effect that updates it.
  const wasPausedRef = useRef(paused);
  // Stops a running reveal fly-in: its per-frame camera writes would undo a pinch zoom.
  const stopRevealRef = useRef<() => void>(() => {});
  const [size, setSize] = useState<{ width: number; height: number }>({ width: 0, height: 0 });
  const [reducedMotion] = useState(prefersReducedMotion);
  const routeScene = useRouteScene({ route, globeRef, containerRef, reducedMotion, fading: routeFading });
  // Without a route, pass the same `labelCities` reference: a new array per render would rebuild the layer.
  const htmlData: readonly object[] =
    routeScene.htmlData.length === 0 ? labelCities : [...labelCities, ...routeScene.htmlData];

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) return;

      setSize({
        width: Math.round(entry.contentRect.width),
        height: Math.round(entry.contentRect.height),
      });
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const globe = globeRef.current;
    if (!globe || size.width === 0 || size.height === 0) return;

    const controls = globe.controls();
    controls.autoRotate = autoRotate && !reducedMotion;
    controls.autoRotateSpeed = AUTO_ROTATE_SPEED;
    controls.enableZoom = false;
    // Pan shifts the camera target: the planet drifts off-center with no way back.
    controls.enablePan = false;

    const target = { lat: pov.lat, lng: pov.lng, altitude: pov.altitude };
    // Appearance: first set or leaving pause. With `reveal`, a fly-in; without it, instant,
    // otherwise the appearance would read as the camera flying in from the previous face.
    const isAppearing = !paused && (!hasSetPovRef.current || wasPausedRef.current);
    hasSetPovRef.current = true;

    if (isAppearing && reveal && !reducedMotion) {
      // Drive the fly-in ourselves, frame by frame: the stock globe.gl tween would overwrite the
      // camera over auto-rotation. Auto-rotation is NOT disabled: damped controls build up speed
      // early, so the spin picks up without a dip at the end of the fly-in.
      const spin = autoRotate ? AUTO_ROTATE_DEG_PER_SEC : 0;
      let rafId = 0;
      let startedAt: number | null = null;
      const step = (now: number) => {
        startedAt ??= now;
        const progress = (now - startedAt) / POV_FLIGHT_MS;
        globe.pointOfView(revealPov(target, progress, spin, POV_FLIGHT_MS), 0);
        if (progress < 1) {
          rafId = requestAnimationFrame(step);
        }
      };

      // Grabbing the sphere aborts the fly-in: per-frame camera overwrites would otherwise pull it
      // back from under the hand. Controls fire `start` only once rotation really began.
      const stopReveal = () => cancelAnimationFrame(rafId);
      controls.addEventListener("start", stopReveal);
      stopRevealRef.current = stopReveal;

      globe.pointOfView(revealPov(target, 0, spin, POV_FLIGHT_MS), 0);
      rafId = requestAnimationFrame(step);
      return () => {
        cancelAnimationFrame(rafId);
        controls.removeEventListener("start", stopReveal);
        stopRevealRef.current = () => {};
      };
    }

    // Fly only for a pov change on a visible globe: a hidden (paused) one has no reason to fly.
    const isInstant = isAppearing || reducedMotion || paused;
    globe.pointOfView(target, isInstant ? 0 : POV_FLIGHT_MS);
  }, [
    paused,
    size.width,
    size.height,
    reducedMotion,
    autoRotate,
    pov.lat,
    pov.lng,
    pov.altitude,
    reveal,
  ]);

  // Declared AFTER the camera effect: within one commit that effect reads the previous value.
  useEffect(() => {
    wasPausedRef.current = paused;
  }, [paused]);

  /*
   * Drag rotation. The canvas spans the whole viewport but the planet occupies only its middle,
   * so hit-testing is against the SPHERE itself (raycast via `toGlobeCoords`), not the element
   * rectangle: a gesture started off the ball does not touch the globe and goes to the page
   * (native scroll on touch). Handler order matters: `enableRotate` is toggled in the capture
   * phase of pointerdown, BEFORE the OrbitControls handler on the canvas, so it starts rotation
   * only for gestures on the sphere. The canvas `touch-action` is reset to auto (OrbitControls
   * sets none, "all touches are mine"), and scroll is suppressed manually only while a sphere
   * drag is in progress (non-passive touchmove + preventDefault).
   */
  useEffect(() => {
    const el = containerRef.current;
    const globe = globeRef.current;
    if (!interactive || !el || !globe || size.width === 0 || size.height === 0) return;

    const controls = globe.controls();
    const canvasEl = globe.renderer().domElement;
    const prevTouchAction = canvasEl.style.touchAction;
    canvasEl.style.touchAction = "auto";

    let isDraggingSphere = false;
    const layoutSize = { width: size.width, height: size.height };
    const isOverSphere = (event: PointerEvent) => hitsSphere(el, globe, layoutSize, event.clientX, event.clientY);

    const handlePointerDown = (event: PointerEvent) => {
      // Multi-touch: while a drag is active ignore new pointers, otherwise a second touch off the
      // sphere aborts the gesture, endDrag hits its early return and autoRotate stays off.
      if (isDraggingSphere) return;

      isDraggingSphere = isOverSphere(event);
      controls.enableRotate = isDraggingSphere;

      if (isDraggingSphere) {
        // While the user holds the planet, auto-rotation must not fight their hand.
        controls.autoRotate = false;
        el.style.cursor = "grabbing";
      }
    };

    const handlePointerMove = (event: PointerEvent) => {
      if (isDraggingSphere) return;

      el.style.cursor = isOverSphere(event) ? "grab" : "";
    };

    const handleTouchMove = (event: TouchEvent) => {
      if (isDraggingSphere) {
        event.preventDefault();
      }
    };

    const endDrag = () => {
      if (!isDraggingSphere) return;

      isDraggingSphere = false;
      controls.autoRotate = autoRotate && !reducedMotion;
      el.style.cursor = "";
    };

    el.addEventListener("pointerdown", handlePointerDown, { capture: true });
    el.addEventListener("pointermove", handlePointerMove);
    el.addEventListener("touchmove", handleTouchMove, { passive: false });
    window.addEventListener("pointerup", endDrag);
    window.addEventListener("pointercancel", endDrag);

    return () => {
      el.removeEventListener("pointerdown", handlePointerDown, { capture: true });
      el.removeEventListener("pointermove", handlePointerMove);
      el.removeEventListener("touchmove", handleTouchMove);
      window.removeEventListener("pointerup", endDrag);
      window.removeEventListener("pointercancel", endDrag);
      canvasEl.style.touchAction = prevTouchAction;
      el.style.cursor = "";
    };
  }, [interactive, autoRotate, reducedMotion, size.width, size.height]);

  /*
   * Label declutter. Near the limb the projection squeezes distances and neighbouring city texts
   * overlap; only the losing label's TEXT is hidden, the city dot is always visible
   * (resolveLabelVisibility decides, applyLabelDeclutter applies). Own rAF loop instead of
   * subscribing to OrbitControls: `pointOfView` flights move the camera behind controls' back, and
   * the "camera matrix unchanged, bail out" gate makes an idle frame free. Within a tick: first a
   * batch of layout reads, then a batch of class writes.
   */
  useEffect(() => {
    const host = containerRef.current;
    const globe = globeRef.current;
    if (!host || !globe || paused || labelCities.length < 2 || size.width === 0 || size.height === 0) {
      return;
    }

    const camera = globe.camera();
    let previousMatrix: number[] = [];
    let lastRunAt = 0;
    let hiddenIds: ReadonlySet<string> = new Set();
    let rafId = 0;

    const tick = (now: number) => {
      rafId = requestAnimationFrame(tick);
      if (now - lastRunAt < DECLUTTER_INTERVAL_MS) return;

      const matrix = camera.matrixWorld.elements;
      if (previousMatrix.length > 0 && matrix.every((value, index) => value === previousMatrix[index])) {
        return;
      }

      previousMatrix = Array.from(matrix);
      lastRunAt = now;

      const hostRect = host.getBoundingClientRect();
      const center = { x: hostRect.left + hostRect.width / 2, y: hostRect.top + hostRect.height / 2 };
      const measured: { wrapper: HTMLElement; box: LabelBox }[] = [];
      for (const wrapper of host.querySelectorAll<HTMLElement>(".globe-label")) {
        // Far-side occlusion owns the wrapper's opacity: labels it hid do not take part in the calculation.
        if (wrapper.style.opacity === "0") continue;

        // Label key is the data attribute from createGlobeLabel: a city name is not unique.
        const id = wrapper.dataset.labelId;
        const nameEl = wrapper.querySelector<HTMLElement>(".globe-label__name");
        if (!id || !nameEl) continue;

        const rect = nameEl.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) continue;

        measured.push({
          wrapper,
          box: { id, left: rect.left, top: rect.top, width: rect.width, height: rect.height },
        });
      }

      hiddenIds = resolveLabelVisibility(
        measured.map((entry) => entry.box),
        center,
        hiddenIds,
      );
      for (const { wrapper, box } of measured) {
        applyLabelDeclutter(wrapper, hiddenIds.has(box.id));
      }
    };

    rafId = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(rafId);
      // Guard against stuck hidden text: the effect may have stopped (labelCities < 2, pause)
      // while globe.gl kept the label DOM; a label must not stay hidden forever.
      for (const wrapper of host.querySelectorAll<HTMLElement>(".globe-label--decluttered")) {
        applyLabelDeclutter(wrapper, false);
      }
    };
  }, [labelCities, paused, size.width, size.height]);

  // A zoom only changes altitude: the next face change or resize flies the camera back to `pov`.
  useGlobeZoom({
    containerRef,
    globeRef,
    enabled: interactive,
    size,
    onZoom: () => stopRevealRef.current(),
  });

  /*
   * WebGL must not spin idle in two cases: the tab is hidden OR the globe is hidden by the route
   * (`paused`, e.g. /journeys, where it is behind the screen's opaque night). Browsers throttle
   * background rAF only unreliably (a window behind another keeps running) and the scene is
   * always animated (auto-rotation + dashed arcs), so stop explicitly: a noticeable battery
   * difference and one live WebGL context for the whole app.
   */
  useEffect(() => {
    const applyPlayState = () => {
      const globe = globeRef.current;
      if (!globe) return;

      if (paused || document.hidden) {
        globe.pauseAnimation();
      } else {
        globe.resumeAnimation();
      }
    };

    applyPlayState();
    document.addEventListener("visibilitychange", applyPlayState);
    return () => document.removeEventListener("visibilitychange", applyPlayState);
    // size.* in the dependencies is NOT for show: `<Globe>` renders only after the first container
    // measurement, so on the first render `globeRef` is empty and applyPlayState exits in vain.
    // Without re-applying once the instance appears, a direct visit to /journeys (the globe is
    // visibility:hidden there but the box exists, so size > 0) would start the globe rAF with paused=true.
  }, [paused, size.width, size.height]);

  return (
    <div ref={containerRef} className={routeFading ? "globe-canvas globe-canvas--route-fading" : "globe-canvas"}>
      {size.width > 0 && size.height > 0 && (
        <Globe
          ref={globeRef}
          width={size.width}
          height={size.height}
          backgroundColor="rgba(0,0,0,0)"
          globeImageUrl={GLOBE_TEXTURE_URL}
          bumpImageUrl={GLOBE_BUMP_URL}
          showAtmosphere
          atmosphereColor={GLOBE_ATMOSPHERE_COLOR}
          atmosphereAltitude={0.24}
          arcsData={arcs as RouteArc[]}
          arcColor={arcColorAccessor}
          arcAltitudeAutoScale={0.42}
          arcStroke={0.6}
          arcDashLength={0.55}
          arcDashGap={0.35}
          arcDashInitialGap={arcDashInitialGapAccessor}
          arcDashAnimateTime={reducedMotion ? 0 : 3800}
          arcsTransitionDuration={reducedMotion ? 0 : 1200}
          pathsData={routeScene.trails as RouteTrail[]}
          pathPoints={pathPointsAccessor}
          pathPointLat={pathPointLatAccessor}
          pathPointLng={pathPointLngAccessor}
          pathPointAlt={pathPointAltAccessor}
          pathColor={pathColorAccessor}
          pathDashLength={0.05}
          pathDashGap={0.02}
          pathDashAnimateTime={reducedMotion ? 0 : 1600}
          pathTransitionDuration={0}
          htmlElementsData={htmlData as object[]}
          htmlLat={htmlLatAccessor}
          htmlLng={htmlLngAccessor}
          htmlAltitude={htmlAltitudeAccessor}
          htmlElement={htmlElementAccessor}
          htmlElementVisibilityModifier={htmlVisibilityModifier}
          // Set positions immediately: with the default 1000ms tween, a vehicle whose coordinates
          // change every frame would pile up tweens and lag behind the trail head.
          htmlTransitionDuration={0}
        />
      )}
    </div>
  );
}

import { useEffect, useMemo, useRef, useState, type RefObject } from "react";
import type { GlobeMethods } from "react-globe.gl";

import type { TransportTypeEnum } from "../../api/sdk";
import carIcon from "../../assets/emoji/car.svg";
import planeIcon from "../../assets/emoji/plane.svg";
import shipIcon from "../../assets/emoji/ship.svg";
import { centralAngleRad } from "./geo";
import {
  apexScale,
  arcAltitude,
  buildTrail,
  greatCirclePoint,
  isRealCity,
  ROUTE_FADE_MS,
  type GlobeRoute,
  type TrailPoint,
} from "./route";
import "./globe-route.css";

/*
 * Imperative part of the globe route scene: pin and vehicle DOM, rAF vehicle motion, and rotating
 * its icon to the on-screen heading. Pure geometry is in route.ts (unit-tested); this module is
 * excluded from coverage (vite.config.ts) because three/WebGL rendering and `getScreenCoords`
 * do not run in jsdom.
 */

// Vehicle icon = the same Noto emoji as in the form select (src/assets/emoji).
// Native orientation (verified by rendering): car and ship are side views, nose LEFT (they cannot
// be rotated, they would flip upside down; only mirror them by direction); the plane is a
// diagonal with its nose UP-RIGHT (~45°) and is rotated to the heading with a 45° offset.
type TransportVisual = {
  icon: string;
  altitude: number;
  durationMs: number;
  orient: "rotate" | "flip";
  nativeFacesRight: boolean;
};

// Arc apex height: noticeable for the plane, half as much for car/ship (a flatter track).
const ARC_ALTITUDE_AIR = 0.14;
const ARC_ALTITUDE_GROUND = ARC_ALTITUDE_AIR / 2;
const TRANSPORT_VISUAL: Record<TransportTypeEnum, TransportVisual> = {
  land: { icon: carIcon, altitude: ARC_ALTITUDE_GROUND, durationMs: 5200, orient: "flip", nativeFacesRight: false },
  air: { icon: planeIcon, altitude: ARC_ALTITUDE_AIR, durationMs: 3600, orient: "rotate", nativeFacesRight: true },
  water: { icon: shipIcon, altitude: ARC_ALTITUDE_GROUND, durationMs: 6000, orient: "flip", nativeFacesRight: false },
};

// Vehicle trail is the product's sunset accent (`--sun`, as a literal: the colour goes into a
// three.js material where CSS variables do not work). RGB without alpha; fading adds the alpha.
const TRAIL_RGB = "232, 147, 92";

// The Noto plane natively points up-right (~45°); rotation to the screen heading = atan2(dy,dx) + 45°.
const ICON_ROTATION_OFFSET_DEG = 45;
// "Look ahead" step for the icon direction (share of the path).
const HEADING_LOOKAHEAD = 0.012;
const PIN_ALTITUDE = 0.01;
const RAD = 180 / Math.PI;

/** Marker class of route DOM elements: the visibility modifier uses it to tell them from labels. */
const ROUTE_ELEMENT_CLASS = "globe-route";
const VEHICLE_ICON_CLASS = "globe-route-vehicle__icon";

type LabelSide = "left" | "right";

/** Route element in the globe.gl html layer (shared with city labels). */
export interface RouteHtmlDatum {
  kind: "route-pin" | "route-vehicle";
  lat: number;
  lng: number;
  alt: number;
  name?: string;
  icon?: string;
  side?: LabelSide;
}

export interface RouteTrail {
  coords: readonly TrailPoint[];
  /** rgba trail colour: alpha drops to zero while the route fades. */
  color: string;
}

export function isRouteDatum(datum: object): datum is RouteHtmlDatum {
  return "kind" in datum;
}

function createPinElement(name: string, side: LabelSide): HTMLElement {
  const wrapper = document.createElement("div");
  // The label goes on the side opposite the route (side) so it does not cover the arc.
  wrapper.className =
    side === "left" ? `${ROUTE_ELEMENT_CLASS} globe-route-pin globe-route-pin--left` : `${ROUTE_ELEMENT_CLASS} globe-route-pin`;

  const dot = document.createElement("span");
  dot.className = "globe-route-pin__dot";

  const label = document.createElement("span");
  label.className = "globe-route-pin__name";
  label.textContent = name;

  wrapper.append(dot, label);
  return wrapper;
}

function createVehicleElement(icon: string): HTMLElement {
  // The outer container is positioned by three-globe; heading rotation is on the nested icon.
  const wrapper = document.createElement("div");
  wrapper.className = `${ROUTE_ELEMENT_CLASS} globe-route-vehicle`;

  const iconEl = document.createElement("div");
  iconEl.className = VEHICLE_ICON_CLASS;

  const img = document.createElement("img");
  img.src = icon;
  img.alt = "";

  iconEl.appendChild(img);
  wrapper.appendChild(iconEl);
  return wrapper;
}

/** DOM of a route element for globe.gl `htmlElement`. */
export function createRouteElement(datum: RouteHtmlDatum): HTMLElement {
  if (datum.kind === "route-vehicle") {
    return createVehicleElement(datum.icon ?? "");
  }

  return createPinElement(datum.name ?? "", datum.side ?? "right");
}

export function isRouteElement(el: HTMLElement): boolean {
  return el.classList.contains(ROUTE_ELEMENT_CLASS);
}

/**
 * Far-side occlusion for route elements: instant, no fade, as globe.gl hid them by default
 * (`obj.visible`) before the layer had a modifier. Inline opacity is left alone so it stays free
 * for the route fade-out.
 */
export function applyRouteVisibility(el: HTMLElement, isVisible: boolean): void {
  el.style.visibility = isVisible ? "" : "hidden";
}

interface RouteSceneOptions {
  route: GlobeRoute | null;
  globeRef: RefObject<GlobeMethods | undefined>;
  containerRef: RefObject<HTMLDivElement | null>;
  reducedMotion: boolean;
  /** The route is fading (leaving the form): the trail loses alpha over ROUTE_FADE_MS, the vehicle keeps going. */
  fading: boolean;
}

interface RouteScene {
  /** Pins and vehicle for the html layer; empty if there are no real cities. */
  htmlData: readonly RouteHtmlDatum[];
  /** Vehicle trail for `pathsData`; empty until the route is complete. */
  trails: readonly RouteTrail[];
}

const NO_ROUTE_HTML: readonly RouteHtmlDatum[] = [];
const NO_TRAILS: readonly RouteTrail[] = [];

/**
 * Route scene: pins only for really picked cities; the arc and vehicle appear once both cities
 * and a transport type are picked. The vehicle moves along a great-circle path leaving a growing
 * dashed trail, with its icon rotated to the heading.
 *
 * While the route animates the hook forces a re-render of its owner every frame: three-globe
 * recomputes positions only when data is set.
 */
export function useRouteScene({
  route,
  globeRef,
  containerRef,
  reducedMotion,
  fading,
}: RouteSceneOptions): RouteScene {
  const progressRef = useRef(0);
  const trailAlphaRef = useRef(1);
  // The increment rebuilds trail/vehicle data each frame. The value itself is unused.
  const [, setFrame] = useState(0);

  const origin = route?.origin ?? null;
  const destination = route?.destination ?? null;
  const transportType = route?.transportType ?? null;
  const originLabel = route?.originLabel ?? "";
  const destinationLabel = route?.destinationLabel ?? "";

  const originReal = isRealCity(origin);
  const destinationReal = isRealCity(destination);
  const showRoute = originReal && destinationReal && transportType !== null;

  const startLat = origin?.latitude ?? 0;
  const startLng = origin?.longitude ?? 0;
  const endLat = destination?.latitude ?? 0;
  const endLng = destination?.longitude ?? 0;

  // Scale arc height by route length, otherwise at zoom an arc between near cities becomes a vertical spike.
  const separation = originReal && destinationReal ? centralAngleRad(startLat, startLng, endLat, endLng) : 0;
  const apex = (transportType ? TRANSPORT_VISUAL[transportType].altitude : 0) * apexScale(separation);

  // Each pin's label goes opposite the other end. Further east is roughly further right on screen.
  const originSide: LabelSide = endLng > startLng ? "left" : "right";
  const destinationSide: LabelSide = startLng > endLng ? "left" : "right";

  // Stable identity per coordinates/label: changing input rebuilds the DOM with new text, while
  // within an animation the DOM is reused.
  const pins = useMemo<readonly RouteHtmlDatum[]>(() => {
    const result: RouteHtmlDatum[] = [];
    if (originReal) {
      result.push({
        kind: "route-pin",
        lat: startLat,
        lng: startLng,
        alt: PIN_ALTITUDE,
        name: originLabel,
        side: originSide,
      });
    }

    if (destinationReal) {
      result.push({
        kind: "route-pin",
        lat: endLat,
        lng: endLng,
        alt: PIN_ALTITUDE,
        name: destinationLabel,
        side: destinationSide,
      });
    }

    return result;
  }, [
    originReal,
    destinationReal,
    startLat,
    startLng,
    endLat,
    endLng,
    originLabel,
    destinationLabel,
    originSide,
    destinationSide,
  ]);

  // Vehicle identity is tied to the icon (a transport change means new DOM). Coordinates are
  // mutable fields that rAF mutates every frame.
  const vehicle = useMemo<RouteHtmlDatum>(
    () => ({
      kind: "route-vehicle",
      lat: 0,
      lng: 0,
      alt: 0,
      icon: transportType ? TRANSPORT_VISUAL[transportType].icon : "",
    }),
    [transportType],
  );

  useEffect(() => {
    if (!showRoute || !transportType) {
      progressRef.current = 0;
      return;
    }

    const config = TRANSPORT_VISUAL[transportType];

    const orientIcon = (t: number) => {
      const globe = globeRef.current;
      const iconEl = containerRef.current?.querySelector<HTMLElement>(`.${VEHICLE_ICON_CLASS}`);
      if (!globe || !iconEl) return;

      const aheadT = t < 1 ? Math.min(1, t + HEADING_LOOKAHEAD) : t - HEADING_LOOKAHEAD;
      const here = greatCirclePoint(startLat, startLng, endLat, endLng, t);
      const ahead = greatCirclePoint(startLat, startLng, endLat, endLng, aheadT);
      const a = globe.getScreenCoords(here.lat, here.lng, arcAltitude(t, apex));
      const b = globe.getScreenCoords(ahead.lat, ahead.lng, arcAltitude(aheadT, apex));
      let dx = b.x - a.x;
      let dy = b.y - a.y;
      if (t >= 1) {
        dx = -dx;
        dy = -dy;
      }

      if (config.orient === "rotate") {
        // Top-down (plane): rotate to the full screen heading.
        iconEl.style.transform = `rotate(${Math.atan2(dy, dx) * RAD + ICON_ROTATION_OFFSET_DEG}deg)`;
      } else {
        // Side view (car/ship): keep upright and only mirror by direction, otherwise moving the
        // other way would turn it upside down.
        const facesRight = dx >= 0;
        iconEl.style.transform = `scaleX(${facesRight === config.nativeFacesRight ? 1 : -1})`;
      }
    };

    const place = (t: number) => {
      const point = greatCirclePoint(startLat, startLng, endLat, endLng, t);
      // The mutation is intentional: three-globe diffs htmlElementsData by object identity and
      // reuses the DOM only if the reference is stable. A new object per frame would rebuild the
      // icon DOM 60 times a second instead of updating its position.
      /* oxlint-disable react/immutability -- see the comment above */
      vehicle.lat = point.lat;
      vehicle.lng = point.lng;
      vehicle.alt = arcAltitude(t, apex);
      /* oxlint-enable react/immutability */
      progressRef.current = t;
      orientIcon(t);
    };

    if (reducedMotion) {
      place(1);
      // `place` mutates `vehicle`/`progressRef` behind React's back; the layer data picks up the
      // final position only through a forced re-render.
      // oxlint-disable-next-line react/set-state-in-effect -- intentional forced re-render after an external mutation, see above
      setFrame((f) => f + 1);
      return;
    }

    const durationMs = config.durationMs;
    let raf = 0;
    let startTs = 0;
    const loop = (ts: number) => {
      if (startTs === 0) startTs = ts;
      place(((ts - startTs) % durationMs) / durationMs);
      setFrame((f) => (f + 1) % 1_000_000);
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, [
    showRoute,
    transportType,
    vehicle,
    apex,
    startLat,
    startLng,
    endLat,
    endLng,
    reducedMotion,
    globeRef,
    containerRef,
  ]);

  // The trail alpha has its own rAF; the per-frame re-render of the motion loop above (running
  // while the route is shown) feeds it into the layer data.
  useEffect(() => {
    if (!fading) {
      trailAlphaRef.current = 1;
      return;
    }

    let raf = 0;
    let startTs = 0;
    const tick = (ts: number) => {
      if (startTs === 0) startTs = ts;
      trailAlphaRef.current = Math.max(0, 1 - (ts - startTs) / ROUTE_FADE_MS);
      if (trailAlphaRef.current > 0) {
        raf = requestAnimationFrame(tick);
      }
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [fading]);

  if (!originReal && !destinationReal) {
    return { htmlData: NO_ROUTE_HTML, trails: NO_TRAILS };
  }

  if (!showRoute) {
    return { htmlData: pins, trails: NO_TRAILS };
  }

  // progressRef is written only inside the rAF callback, and this render is forced by the same
  // callback via setFrame, so the value has settled by the time it is read.
  /* oxlint-disable react/refs -- intentional read outside an effect, see the comment above */
  const trails = [
    {
      coords: buildTrail(startLat, startLng, endLat, endLng, apex, progressRef.current),
      color: `rgba(${TRAIL_RGB}, ${trailAlphaRef.current})`,
    },
  ];
  /* oxlint-enable react/refs */
  return { htmlData: [...pins, vehicle], trails };
}

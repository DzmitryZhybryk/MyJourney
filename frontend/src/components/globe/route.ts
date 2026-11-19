import type { CitySearchItem, TransportTypeEnum } from "../../api/sdk";
import type { GlobePov } from "./GlobeCanvas";
import { centralAngleRad } from "./geo";

/*
 * Pure geometry of a trip route on the globe: great-circle interpolation, arc height, camera
 * auto-zoom for the route length, trail sampling. Split out of the scene (routeScene.ts) so the
 * math can be unit-tested: three/WebGL rendering is not testable in jsdom, these functions are
 * deterministic.
 */

const DEG = Math.PI / 180;
const RAD = 180 / Math.PI;

// Camera: auto-zoom by city proximity. The closer the cities, the stronger the zoom (lower
// altitude), so the route takes ~ROUTE_VIEWPORT_SPAN of the view, within [MIN, MAX].
const CAMERA_FOV_DEG = 50; // field of view of the three.js camera in globe.gl
const ROUTE_VIEWPORT_SPAN = 0.1; // target share of the view for the route (larger = closer zoom)
// Far limit (cities far apart / one picked / form empty). Also the camera altitude of the
// dashboard face: at equal frame scale the sphere on the form and on home is the same size, so
// the transition between them is a pure pan without ballooning (see SCREEN_POV in PersistentGlobeHost).
export const CAMERA_MAX_ALTITUDE = 2.4;
export const CAMERA_MIN_ALTITUDE = 0.12; // near limit (do not zoom closer than this)
// Arc height is normalized to this angular size: far routes get a "full" arc, near ones scale
// down, otherwise a zoomed-in arc becomes a vertical spike.
const ARC_REFERENCE_SEPARATION_RAD = (50 * Math.PI) / 180;
const TRAIL_SAMPLES = 96;

/**
 * Fade-out duration of the route when leaving the form for /home. The same number is in
 * globe-route.css (pin/icon opacity transition): keep them in sync.
 * Lives here, not in routeScene.ts: the host imports it directly, and a value import from the
 * scene would drag its DOM code, CSS and SVG into the host chunk loaded on every page.
 */
export const ROUTE_FADE_MS = 700;

export type GeoPoint = { lat: number; lng: number };
export type TrailPoint = { lat: number; lng: number; alt: number };

/** Trip route that the add-journey form hands to the globe. */
export interface GlobeRoute {
  origin: CitySearchItem | null;
  destination: CitySearchItem | null;
  transportType: TransportTypeEnum | null;
  originLabel: string;
  destinationLabel: string;
}

// Camera view while no city is picked (neutral, no demo route).
const DEFAULT_ROUTE_VIEW: GeoPoint = { lat: 20, lng: 0 };
// Share of latitude the far zoom pulls toward the equator: a view beside the form, not from the pole.
const FAR_ZOOM_EQUATOR_PULL = 0.4;

/** Point on the great circle between two coordinates at parameter t in [0, 1] (slerp). */
export function greatCirclePoint(
  startLat: number,
  startLng: number,
  endLat: number,
  endLng: number,
  t: number,
): GeoPoint {
  const phi1 = startLat * DEG;
  const lam1 = startLng * DEG;
  const phi2 = endLat * DEG;
  const lam2 = endLng * DEG;

  const a = Math.sin((phi2 - phi1) / 2) ** 2 + Math.cos(phi1) * Math.cos(phi2) * Math.sin((lam2 - lam1) / 2) ** 2;
  const delta = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  if (delta < 1e-6) {
    return { lat: startLat, lng: startLng };
  }

  const ka = Math.sin((1 - t) * delta) / Math.sin(delta);
  const kb = Math.sin(t * delta) / Math.sin(delta);
  const x = ka * Math.cos(phi1) * Math.cos(lam1) + kb * Math.cos(phi2) * Math.cos(lam2);
  const y = ka * Math.cos(phi1) * Math.sin(lam1) + kb * Math.cos(phi2) * Math.sin(lam2);
  const z = ka * Math.sin(phi1) + kb * Math.sin(phi2);

  return { lat: Math.atan2(z, Math.hypot(x, y)) * RAD, lng: Math.atan2(y, x) * RAD };
}

/** Height above the surface at a route point: 0 at the ends, apex in the middle. */
export function arcAltitude(t: number, apex: number): number {
  return Math.sin(Math.PI * t) * apex;
}

export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

/**
 * Camera height (globe.gl altitude) for the route's angular size: closer cities mean lower
 * altitude (stronger zoom). Geometry: a camera at distance d from the center sees the route ends
 * at angle targetHalfAngle; the result is clamped to [MIN, MAX].
 */
export function altitudeForSeparation(separationRad: number): number {
  if (separationRad <= 0) {
    return CAMERA_MAX_ALTITUDE;
  }

  const targetHalfAngle = (ROUTE_VIEWPORT_SPAN * CAMERA_FOV_DEG * DEG) / 2;
  const half = separationRad / 2;
  const cameraDistance = Math.cos(half) + Math.sin(half) / Math.tan(targetHalfAngle);
  return clamp(cameraDistance - 1, CAMERA_MIN_ALTITUDE, CAMERA_MAX_ALTITUDE);
}

/**
 * Arc height multiplier by route length (0..1): near cities scale the arc down (sqrt, so medium
 * routes are not too flat), far ones get a "full" arc.
 */
export function apexScale(separationRad: number): number {
  return Math.sqrt(Math.min(1, separationRad / ARC_REFERENCE_SEPARATION_RAD));
}

/** Trail points up to the current progress (the head sits exactly under the icon). */
export function buildTrail(
  startLat: number,
  startLng: number,
  endLat: number,
  endLng: number,
  apex: number,
  progress: number,
): readonly TrailPoint[] {
  const points: TrailPoint[] = [];
  for (let i = 0; i <= TRAIL_SAMPLES; i += 1) {
    const tau = i / TRAIL_SAMPLES;
    if (tau > progress) break;

    const point = greatCirclePoint(startLat, startLng, endLat, endLng, tau);
    points.push({ lat: point.lat, lng: point.lng, alt: arcAltitude(tau, apex) });
  }

  // Pin the trail head exactly under the icon (exact progress, not the nearest sample).
  const head = greatCirclePoint(startLat, startLng, endLat, endLng, progress);
  points.push({ lat: head.lat, lng: head.lng, alt: arcAltitude(progress, apex) });
  return points;
}

/** A city is "real" (picked from autocomplete) if it has coordinates. */
export function isRealCity(city: CitySearchItem | null): city is CitySearchItem {
  return city !== null && (city.latitude !== 0 || city.longitude !== 0);
}

/**
 * Camera point of view for the route: the midpoint of the path (zoom by distance), or the single
 * picked city, or a neutral view while nothing is picked. Returns the `pointOfView` for globe.gl.
 */
export function routeCameraPov(route: GlobeRoute | null): GlobePov {
  const origin = route?.origin ?? null;
  const destination = route?.destination ?? null;

  let target = DEFAULT_ROUTE_VIEW;
  let altitude = CAMERA_MAX_ALTITUDE;
  if (isRealCity(origin) && isRealCity(destination)) {
    target = greatCirclePoint(origin.latitude, origin.longitude, destination.latitude, destination.longitude, 0.5);
    altitude = altitudeForSeparation(
      centralAngleRad(origin.latitude, origin.longitude, destination.latitude, destination.longitude),
    );
  } else if (isRealCity(origin)) {
    target = { lat: origin.latitude, lng: origin.longitude };
  } else if (isRealCity(destination)) {
    target = { lat: destination.latitude, lng: destination.longitude };
  }

  // At close zoom center exactly on the route, otherwise the zoom pushes the cities out of frame.
  const zoomT = (altitude - CAMERA_MIN_ALTITUDE) / (CAMERA_MAX_ALTITUDE - CAMERA_MIN_ALTITUDE);
  const latFactor = 1 - FAR_ZOOM_EQUATOR_PULL * zoomT;
  return { lat: target.lat * latFactor, lng: target.lng, altitude };
}

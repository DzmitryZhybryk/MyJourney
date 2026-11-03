import { useEffect, useRef, type RefObject } from "react";
import type { GlobeMethods } from "react-globe.gl";

import { CAMERA_MAX_ALTITUDE, clamp } from "./route";

// Zoom change per pixel of wheel scroll or trackpad pinch, the same as on the 2D map.
const WHEEL_ZOOM_SPEED = 0.01;
/**
 * Closest a pinch brings the camera: the planet looks about three times larger than on the home face.
 * The route framing on the journey form may go lower (`CAMERA_MIN_ALTITUDE`).
 */
const ZOOM_MIN_ALTITUDE = 0.48;

export interface LayoutSize {
  width: number;
  height: number;
}

/** Safari sends a trackpad pinch (and a touch pinch on iOS) as a non-standard GestureEvent. */
interface SafariGestureEvent extends UIEvent {
  scale: number;
  clientX: number;
  clientY: number;
}

/**
 * Whether a screen point lies on the sphere itself, not just on the canvas around it. The raycast
 * normalizes by the canvas LAYOUT size while the canvas sits in a transformed (scaled) stage, so the
 * screen point is converted through the actual rect first.
 */
export function hitsSphere(
  el: HTMLElement,
  globe: GlobeMethods,
  layoutSize: LayoutSize,
  clientX: number,
  clientY: number,
): boolean {
  const rect = el.getBoundingClientRect();
  if (rect.width === 0 || rect.height === 0) return false;

  const x = ((clientX - rect.left) * layoutSize.width) / rect.width;
  const y = ((clientY - rect.top) * layoutSize.height) / rect.height;
  return globe.toGlobeCoords(x, y) !== null;
}

function touchDistance(touches: TouchList): number {
  const [first, second] = [touches[0], touches[1]];
  return Math.hypot(second.clientX - first.clientX, second.clientY - first.clientY);
}

interface GlobeZoomOptions {
  containerRef: RefObject<HTMLDivElement | null>;
  globeRef: RefObject<GlobeMethods | undefined>;
  enabled: boolean;
  size: LayoutSize;
  /** Called on each zoom step: the caller stops a camera animation that would overwrite it. */
  onZoom: () => void;
}

/**
 * Pinch zoom of the globe camera, only over the sphere: trackpad pinch (wheel with `ctrlKey`,
 * GestureEvent in Safari) and two fingers on touch. Altitude is clamped to the camera limits.
 * A plain wheel is never taken, so the page still scrolls over the planet; that is why this is not
 * OrbitControls' `enableZoom`, which zooms on every wheel.
 */
export function useGlobeZoom({ containerRef, globeRef, enabled, size, onZoom }: GlobeZoomOptions): void {
  const { width, height } = size;
  const onZoomRef = useRef(onZoom);
  useEffect(() => {
    onZoomRef.current = onZoom;
  });

  useEffect(() => {
    const el = containerRef.current;
    const globe = globeRef.current;
    if (!enabled || !el || !globe || width === 0 || height === 0) return;

    const isOverSphere = (clientX: number, clientY: number) => hitsSphere(el, globe, { width, height }, clientX, clientY);
    const currentAltitude = () => globe.pointOfView().altitude;
    const zoomTo = (altitude: number) => {
      onZoomRef.current();
      // Below the pinch limit (a close route framing) a zoom-in holds the camera instead of jumping
      // out to the limit; a zoom-out works as usual.
      const floor = Math.min(ZOOM_MIN_ALTITUDE, currentAltitude());
      globe.pointOfView({ altitude: clamp(altitude, floor, CAMERA_MAX_ALTITUDE) }, 0);
    };

    const handleWheel = (event: WheelEvent) => {
      if (!event.ctrlKey || !isOverSphere(event.clientX, event.clientY)) return;

      event.preventDefault();
      zoomTo(currentAltitude() * Math.exp(event.deltaY * WHEEL_ZOOM_SPEED));
    };

    // One pinch has one zoom source. iOS fires gesture events alongside the touch pinch, and its
    // `gesturestart` arrives BEFORE the second finger's `touchstart`; the touch pinch then takes over.
    let pinchDistance: number | null = null;
    let gestureStartAltitude: number | null = null;

    const handleTouchStart = (event: TouchEvent) => {
      if (event.touches.length !== 2) return;

      const [first, second] = [event.touches[0], event.touches[1]];
      const isOnSphere = isOverSphere((first.clientX + second.clientX) / 2, (first.clientY + second.clientY) / 2);
      pinchDistance = isOnSphere ? touchDistance(event.touches) : null;
      if (isOnSphere) {
        gestureStartAltitude = null;
      }
    };
    const handleTouchMove = (event: TouchEvent) => {
      if (pinchDistance === null || event.touches.length !== 2) return;

      event.preventDefault();
      const distance = touchDistance(event.touches);
      if (pinchDistance > 0 && distance > 0) {
        zoomTo((currentAltitude() * pinchDistance) / distance);
      }
      pinchDistance = distance;
    };
    const handleTouchEnd = (event: TouchEvent) => {
      if (event.touches.length < 2) {
        pinchDistance = null;
      }
    };

    const handleGestureStart = (event: Event) => {
      const gesture = event as SafariGestureEvent;
      if (pinchDistance !== null || !isOverSphere(gesture.clientX, gesture.clientY)) return;

      event.preventDefault();
      gestureStartAltitude = currentAltitude();
    };
    const handleGestureChange = (event: Event) => {
      if (gestureStartAltitude === null) return;

      event.preventDefault();
      const { scale } = event as SafariGestureEvent;
      if (scale > 0) {
        zoomTo(gestureStartAltitude / scale);
      }
    };
    const handleGestureEnd = () => {
      gestureStartAltitude = null;
    };

    el.addEventListener("wheel", handleWheel, { passive: false });
    el.addEventListener("touchstart", handleTouchStart);
    el.addEventListener("touchmove", handleTouchMove, { passive: false });
    el.addEventListener("touchend", handleTouchEnd);
    el.addEventListener("touchcancel", handleTouchEnd);
    el.addEventListener("gesturestart", handleGestureStart);
    el.addEventListener("gesturechange", handleGestureChange);
    el.addEventListener("gestureend", handleGestureEnd);
    return () => {
      el.removeEventListener("wheel", handleWheel);
      el.removeEventListener("touchstart", handleTouchStart);
      el.removeEventListener("touchmove", handleTouchMove);
      el.removeEventListener("touchend", handleTouchEnd);
      el.removeEventListener("touchcancel", handleTouchEnd);
      el.removeEventListener("gesturestart", handleGestureStart);
      el.removeEventListener("gesturechange", handleGestureChange);
      el.removeEventListener("gestureend", handleGestureEnd);
    };
  }, [enabled, width, height, containerRef, globeRef]);
}

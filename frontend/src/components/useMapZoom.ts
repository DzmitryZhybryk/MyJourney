import { useEffect, useRef, useState, type RefObject } from "react";

import { isSameView, isWorldView, panView, zoomView, type ViewBox } from "./worldProjection";

// Zoom change per pixel of wheel scroll or trackpad pinch.
const WHEEL_ZOOM_SPEED = 0.01;

/** Safari sends a trackpad pinch as a non-standard GestureEvent, not a wheel event with `ctrlKey`. */
interface SafariGestureEvent extends UIEvent {
  scale: number;
  clientX: number;
  clientY: number;
}

interface ScreenPosition {
  x: number;
  y: number;
}

function distance(from: ScreenPosition, to: ScreenPosition): number {
  return Math.hypot(to.x - from.x, to.y - from.y);
}

/**
 * Zoom and pan of the map by gestures, only over the map itself; the rest of the page stays put.
 *
 * Zoom: trackpad pinch (wheel with `ctrlKey`, GestureEvent in Safari) and two fingers on touch.
 * A zoomed map is panned by drag and scroll. Double click restores the initial view. While the
 * whole map is visible, scroll and vertical swipe go to the page.
 *
 * Gestures are listened for on `canvasRef`; the on-screen size of `svgRef` converts pixels to
 * canvas units. A new `initialView` replaces the view only while the user has not changed it; a
 * new `resetKey` drops the user's zoom and follows `initialView` again.
 * Returns the current visible area.
 */
export function useMapZoom(
  canvasRef: RefObject<HTMLElement | null>,
  svgRef: RefObject<SVGSVGElement | null>,
  initialView: ViewBox,
  resetKey?: unknown,
): ViewBox {
  const [trackedInitialView, setTrackedInitialView] = useState(initialView);
  const [view, setView] = useState(initialView);
  const [trackedResetKey, setTrackedResetKey] = useState(resetKey);
  if (trackedResetKey !== resetKey) {
    setTrackedResetKey(resetKey);
    setTrackedInitialView(initialView);
    setView(initialView);
  } else if (trackedInitialView !== initialView) {
    setTrackedInitialView(initialView);
    // A view the user already changed is not overwritten by a new initial one (e.g. after a resize).
    if (isSameView(view, trackedInitialView)) {
      setView(initialView);
    }
  }

  // Handlers subscribe once and read the current and initial view from here.
  const viewRef = useRef(view);
  const initialViewRef = useRef(initialView);
  useEffect(() => {
    viewRef.current = view;
    initialViewRef.current = initialView;
  });

  useEffect(() => {
    const canvas = canvasRef.current;
    const svg = svgRef.current;
    /* v8 ignore next 3 -- both nodes render with the map, the effect runs after mount */
    if (!canvas || !svg) {
      return;
    }

    const apply = (next: ViewBox) => {
      viewRef.current = next;
      setView(next);
    };

    // Canvas units per screen pixel, and which canvas point lies under a screen point.
    const unitsPerPx = () => viewRef.current.width / svg.getBoundingClientRect().width;
    const toCanvas = (clientX: number, clientY: number): ScreenPosition => {
      const rect = svg.getBoundingClientRect();
      const scale = viewRef.current.width / rect.width;
      return {
        x: viewRef.current.x + (clientX - rect.left) * scale,
        y: viewRef.current.y + (clientY - rect.top) * scale,
      };
    };

    const handleWheel = (event: WheelEvent) => {
      if (event.ctrlKey) {
        event.preventDefault();
        const anchor = toCanvas(event.clientX, event.clientY);
        apply(zoomView(viewRef.current, Math.exp(-event.deltaY * WHEEL_ZOOM_SPEED), anchor.x, anchor.y));
        return;
      }

      if (isWorldView(viewRef.current)) {
        return;
      }

      event.preventDefault();
      const scale = unitsPerPx();
      apply(panView(viewRef.current, event.deltaX * scale, event.deltaY * scale));
    };

    let gestureStart: { view: ViewBox; anchor: ScreenPosition } | null = null;
    const handleGestureStart = (event: Event) => {
      event.preventDefault();
      const gesture = event as SafariGestureEvent;
      gestureStart = { view: viewRef.current, anchor: toCanvas(gesture.clientX, gesture.clientY) };
    };
    const handleGestureChange = (event: Event) => {
      event.preventDefault();
      if (gestureStart) {
        const { scale } = event as SafariGestureEvent;
        apply(zoomView(gestureStart.view, scale, gestureStart.anchor.x, gestureStart.anchor.y));
      }
    };
    const handleGestureEnd = (event: Event) => {
      event.preventDefault();
      gestureStart = null;
    };

    // Active touches and the pressed mouse button: one pans, two pinch.
    const pointers = new Map<number, ScreenPosition>();
    const handlePointerDown = (event: PointerEvent) => {
      if (event.pointerType === "mouse" && event.button !== 0) {
        return;
      }

      pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
      canvas.setPointerCapture(event.pointerId);
    };
    const handlePointerMove = (event: PointerEvent) => {
      const previous = pointers.get(event.pointerId);
      if (!previous) {
        return;
      }

      const current = { x: event.clientX, y: event.clientY };
      const other = [...pointers].find(([pointerId]) => pointerId !== event.pointerId)?.[1];
      if (other) {
        const before = distance(previous, other);
        if (before > 0) {
          const anchor = toCanvas((current.x + other.x) / 2, (current.y + other.y) / 2);
          apply(zoomView(viewRef.current, distance(current, other) / before, anchor.x, anchor.y));
        }
      } else if (!isWorldView(viewRef.current)) {
        const scale = unitsPerPx();
        apply(panView(viewRef.current, (previous.x - current.x) * scale, (previous.y - current.y) * scale));
      }

      pointers.set(event.pointerId, current);
    };
    const handlePointerEnd = (event: PointerEvent) => {
      pointers.delete(event.pointerId);
    };
    const handleDoubleClick = () => apply(initialViewRef.current);

    canvas.addEventListener("wheel", handleWheel, { passive: false });
    canvas.addEventListener("gesturestart", handleGestureStart);
    canvas.addEventListener("gesturechange", handleGestureChange);
    canvas.addEventListener("gestureend", handleGestureEnd);
    canvas.addEventListener("pointerdown", handlePointerDown);
    canvas.addEventListener("pointermove", handlePointerMove);
    canvas.addEventListener("pointerup", handlePointerEnd);
    canvas.addEventListener("pointercancel", handlePointerEnd);
    canvas.addEventListener("dblclick", handleDoubleClick);
    return () => {
      canvas.removeEventListener("wheel", handleWheel);
      canvas.removeEventListener("gesturestart", handleGestureStart);
      canvas.removeEventListener("gesturechange", handleGestureChange);
      canvas.removeEventListener("gestureend", handleGestureEnd);
      canvas.removeEventListener("pointerdown", handlePointerDown);
      canvas.removeEventListener("pointermove", handlePointerMove);
      canvas.removeEventListener("pointerup", handlePointerEnd);
      canvas.removeEventListener("pointercancel", handlePointerEnd);
      canvas.removeEventListener("dblclick", handleDoubleClick);
    };
  }, [canvasRef, svgRef]);

  return view;
}

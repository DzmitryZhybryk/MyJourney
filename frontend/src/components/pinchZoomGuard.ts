/**
 * Turns off zoom gestures for the page: trackpad pinch (wheel with `ctrlKey`, GestureEvent in
 * Safari) and a two-finger pinch on touch. Maps and the globe handle these gestures on their own
 * elements (`useMapZoom`, `useGlobeZoom`); everywhere else they do nothing.
 *
 * Keyboard zoom (Cmd +/−) stays on: it is a deliberate way to enlarge text, not a stray gesture.
 * Returns a function that removes the listeners.
 */
export function installPinchZoomGuard(target: Document = document): () => void {
  const handleWheel = (event: WheelEvent) => {
    if (event.ctrlKey) {
      event.preventDefault();
    }
  };
  const handleGesture = (event: Event) => event.preventDefault();
  const handleTouchMove = (event: TouchEvent) => {
    if (event.touches.length > 1) {
      event.preventDefault();
    }
  };

  // Document-level wheel and touch listeners are passive by default, and a passive one cannot cancel.
  target.addEventListener("wheel", handleWheel, { passive: false });
  target.addEventListener("gesturestart", handleGesture);
  target.addEventListener("gesturechange", handleGesture);
  target.addEventListener("touchmove", handleTouchMove, { passive: false });
  return () => {
    target.removeEventListener("wheel", handleWheel);
    target.removeEventListener("gesturestart", handleGesture);
    target.removeEventListener("gesturechange", handleGesture);
    target.removeEventListener("touchmove", handleTouchMove);
  };
}

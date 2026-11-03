import { afterEach, describe, expect, it } from "vitest";

import { installPinchZoomGuard } from "./pinchZoomGuard";

/** jsdom has no Touch constructor: a touch event is a plain event with a `touches` list. */
function touchMove(fingers: number): Event {
  const touches = Array.from({ length: fingers }, (_, index) => ({ clientX: index * 10, clientY: 0 }));
  return Object.assign(new Event("touchmove", { bubbles: true, cancelable: true }), { touches });
}

function dispatchOnPage(event: Event): Event {
  document.body.dispatchEvent(event);
  return event;
}

let uninstall: (() => void) | null = null;

afterEach(() => {
  uninstall?.();
  uninstall = null;
});

describe("installPinchZoomGuard", () => {
  it("щипок тачпада (колесо с ctrlKey) страницу не масштабирует", () => {
    uninstall = installPinchZoomGuard();

    const pinch = dispatchOnPage(new WheelEvent("wheel", { bubbles: true, cancelable: true, ctrlKey: true }));

    expect(pinch.defaultPrevented).toBe(true);
  });

  it("обычная прокрутка колесом остаётся странице", () => {
    uninstall = installPinchZoomGuard();

    const scroll = dispatchOnPage(new WheelEvent("wheel", { bubbles: true, cancelable: true, deltaY: 40 }));

    expect(scroll.defaultPrevented).toBe(false);
  });

  it("щипок тачпада в Safari страницу не масштабирует", () => {
    uninstall = installPinchZoomGuard();

    const start = dispatchOnPage(new Event("gesturestart", { bubbles: true, cancelable: true }));
    const change = dispatchOnPage(new Event("gesturechange", { bubbles: true, cancelable: true }));

    expect(start.defaultPrevented).toBe(true);
    expect(change.defaultPrevented).toBe(true);
  });

  it("щипок двумя пальцами глушится, свайп одним пальцем — нет", () => {
    uninstall = installPinchZoomGuard();

    expect(dispatchOnPage(touchMove(2)).defaultPrevented).toBe(true);
    expect(dispatchOnPage(touchMove(1)).defaultPrevented).toBe(false);
  });

  it("после снятия жесты снова достаются браузеру", () => {
    installPinchZoomGuard()();

    const pinch = dispatchOnPage(new WheelEvent("wheel", { bubbles: true, cancelable: true, ctrlKey: true }));
    const gesture = dispatchOnPage(new Event("gesturestart", { bubbles: true, cancelable: true }));
    const change = dispatchOnPage(new Event("gesturechange", { bubbles: true, cancelable: true }));

    expect(pinch.defaultPrevented).toBe(false);
    expect(gesture.defaultPrevented).toBe(false);
    expect(change.defaultPrevented).toBe(false);
    expect(dispatchOnPage(touchMove(2)).defaultPrevented).toBe(false);
  });
});

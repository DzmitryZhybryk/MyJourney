import { renderHook } from "@testing-library/react";
import type { GlobeMethods } from "react-globe.gl";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CAMERA_MAX_ALTITUDE, CAMERA_MIN_ALTITUDE } from "./route";
import { hitsSphere, useGlobeZoom } from "./useGlobeZoom";

const LAYOUT = { width: 800, height: 600 };
const START_ALTITUDE = 1.6;
// The pinch limit agreed with the owner; a literal, so a changed constant fails the test.
const PINCH_MIN_ALTITUDE = 0.48;
// The sphere occupies the left half of the canvas: points there hit it, points to the right miss.
const ON_SPHERE = { clientX: 200, clientY: 300 };
const OFF_SPHERE = { clientX: 700, clientY: 300 };

/** The WebGL boundary: a camera that keeps its altitude and a raycast against the left half. */
function createGlobe(startAltitude = START_ALTITUDE) {
  let altitude = startAltitude;
  const pointOfView = (pov?: { altitude?: number }) => {
    if (pov === undefined) {
      return { lat: 0, lng: 0, altitude };
    }
    altitude = pov.altitude ?? altitude;
    return undefined;
  };
  const toGlobeCoords = vi.fn((x: number) => (x < LAYOUT.width / 2 ? { lat: 0, lng: 0 } : null));
  const globe = { pointOfView, toGlobeCoords } as unknown as GlobeMethods;
  return { globe, toGlobeCoords, altitude: () => altitude };
}

function wheel(point: { clientX: number; clientY: number }, deltaY: number, ctrlKey: boolean): WheelEvent {
  return new WheelEvent("wheel", { bubbles: true, cancelable: true, ctrlKey, deltaY, ...point });
}

/** Safari sends a pinch as separate events with `scale`. */
function gesture(type: string, scale: number, point: { clientX: number; clientY: number }): Event {
  return Object.assign(new Event(type, { bubbles: true, cancelable: true }), { scale, ...point });
}

/** jsdom has no Touch constructor: a touch event is a plain event with a `touches` list. */
function touch(type: string, touches: readonly { clientX: number; clientY: number }[]): Event {
  return Object.assign(new Event(type, { bubbles: true, cancelable: true }), { touches });
}

/** Two fingers around `center`, `spread` pixels apart horizontally. */
function fingers(center: { clientX: number; clientY: number }, spread: number) {
  return [
    { clientX: center.clientX - spread / 2, clientY: center.clientY },
    { clientX: center.clientX + spread / 2, clientY: center.clientY },
  ];
}

describe("useGlobeZoom", () => {
  let container: HTMLDivElement;
  let camera: ReturnType<typeof createGlobe>;
  const onZoom = vi.fn();

  beforeEach(() => {
    onZoom.mockReset();
    camera = createGlobe();
    container = document.createElement("div");
    vi.spyOn(container, "getBoundingClientRect").mockReturnValue(new DOMRect(0, 0, LAYOUT.width, LAYOUT.height));
  });

  function renderZoom(overrides: Partial<Parameters<typeof useGlobeZoom>[0]> = {}) {
    return renderHook(() =>
      useGlobeZoom({
        containerRef: { current: container },
        globeRef: { current: camera.globe },
        enabled: true,
        size: LAYOUT,
        onZoom,
        ...overrides,
      }),
    );
  }

  function dispatch(event: Event): Event {
    container.dispatchEvent(event);
    return event;
  }

  it("щипок тачпада над сферой приближает камеру и не достаётся странице", () => {
    renderZoom();

    const pinch = dispatch(wheel(ON_SPHERE, -20, true));

    expect(camera.altitude()).toBeCloseTo(START_ALTITUDE * Math.exp(-0.2));
    expect(pinch.defaultPrevented).toBe(true);
    expect(onZoom).toHaveBeenCalled();
  });

  it("разведение тачпада отдаляет камеру", () => {
    renderZoom();

    dispatch(wheel(ON_SPHERE, 20, true));

    expect(camera.altitude()).toBeCloseTo(START_ALTITUDE * Math.exp(0.2));
  });

  it("высота камеры не выходит за пределы ни при приближении, ни при отдалении", () => {
    renderZoom();

    dispatch(wheel(ON_SPHERE, -1000, true));
    expect(camera.altitude()).toBe(PINCH_MIN_ALTITUDE);

    dispatch(wheel(ON_SPHERE, 1000, true));
    expect(camera.altitude()).toBe(CAMERA_MAX_ALTITUDE);
  });

  it("ниже предела щипка (кадр короткого маршрута) приближение камеру держит, отдаление плавное", () => {
    camera = createGlobe(CAMERA_MIN_ALTITUDE);
    renderZoom();

    dispatch(wheel(ON_SPHERE, -1, true));
    expect(camera.altitude()).toBe(CAMERA_MIN_ALTITUDE);

    dispatch(wheel(ON_SPHERE, 10, true));
    expect(camera.altitude()).toBeCloseTo(CAMERA_MIN_ALTITUDE * Math.exp(0.1));
  });

  it("обычная прокрутка над сферой камеру не трогает и остаётся странице", () => {
    renderZoom();

    const scroll = dispatch(wheel(ON_SPHERE, -20, false));

    expect(camera.altitude()).toBe(START_ALTITUDE);
    expect(scroll.defaultPrevented).toBe(false);
  });

  it("щипок мимо сферы камеру не трогает", () => {
    renderZoom();

    dispatch(wheel(OFF_SPHERE, -20, true));
    dispatch(gesture("gesturestart", 1, OFF_SPHERE));
    dispatch(gesture("gesturechange", 2, OFF_SPHERE));
    dispatch(touch("touchstart", fingers(OFF_SPHERE, 100)));
    dispatch(touch("touchmove", fingers(OFF_SPHERE, 200)));

    expect(camera.altitude()).toBe(START_ALTITUDE);
    expect(onZoom).not.toHaveBeenCalled();
  });

  it("щипок тачпада в Safari считает масштаб от начала жеста", () => {
    renderZoom();

    dispatch(gesture("gesturestart", 1, ON_SPHERE));
    const change = dispatch(gesture("gesturechange", 2, ON_SPHERE));
    dispatch(gesture("gesturechange", 3, ON_SPHERE));
    dispatch(gesture("gestureend", 3, ON_SPHERE));

    expect(camera.altitude()).toBeCloseTo(START_ALTITUDE / 3);
    expect(change.defaultPrevented).toBe(true);

    // After the gesture ends, a stray change event does not zoom.
    dispatch(gesture("gesturechange", 1, ON_SPHERE));
    expect(camera.altitude()).toBeCloseTo(START_ALTITUDE / 3);
  });

  it("щипок двумя пальцами на сфере приближает камеру по разведению пальцев", () => {
    renderZoom();

    dispatch(touch("touchstart", fingers(ON_SPHERE, 100)));
    const move = dispatch(touch("touchmove", fingers(ON_SPHERE, 200)));

    expect(camera.altitude()).toBeCloseTo(START_ALTITUDE / 2);
    expect(move.defaultPrevented).toBe(true);

    dispatch(touch("touchend", fingers(ON_SPHERE, 200).slice(0, 1)));
    dispatch(touch("touchmove", fingers(ON_SPHERE, 400)));
    expect(camera.altitude()).toBeCloseTo(START_ALTITUDE / 2);
  });

  // iOS order per Apple's docs: first finger touchstart → gesturestart → second finger touchstart.
  // The order of the following gesturechange / touchmove is not fixed, so both are covered.
  it.each([
    ["gesturechange первым", ["gesturechange", "touchmove"]],
    ["touchmove первым", ["touchmove", "gesturechange"]],
  ] as const)("на iOS один щипок зумит один раз (%s)", (_, order) => {
    renderZoom();

    dispatch(touch("touchstart", fingers(ON_SPHERE, 100).slice(0, 1)));
    dispatch(gesture("gesturestart", 1, ON_SPHERE));
    dispatch(touch("touchstart", fingers(ON_SPHERE, 100)));
    for (const type of order) {
      dispatch(type === "touchmove" ? touch(type, fingers(ON_SPHERE, 200)) : gesture(type, 2, ON_SPHERE));
    }

    expect(camera.altitude()).toBeCloseTo(START_ALTITUDE / 2);
  });

  it("жест Safari, начатый вторым пальцем после щипка пальцами, не зумит второй раз", () => {
    renderZoom();

    dispatch(touch("touchstart", fingers(ON_SPHERE, 100)));
    dispatch(gesture("gesturestart", 1, ON_SPHERE));
    dispatch(touch("touchmove", fingers(ON_SPHERE, 200)));
    dispatch(gesture("gesturechange", 2, ON_SPHERE));

    expect(camera.altitude()).toBeCloseTo(START_ALTITUDE / 2);
  });

  it("выключенный зум и холст без размера на жесты не отвечают", () => {
    const { unmount } = renderZoom({ enabled: false });
    dispatch(wheel(ON_SPHERE, -20, true));
    unmount();

    renderZoom({ size: { width: 0, height: 0 } });
    dispatch(wheel(ON_SPHERE, -20, true));

    expect(camera.altitude()).toBe(START_ALTITUDE);
  });

  it("после размонтирования жесты камеру не трогают", () => {
    const { unmount } = renderZoom();
    unmount();

    dispatch(wheel(ON_SPHERE, -20, true));
    dispatch(gesture("gesturestart", 1, ON_SPHERE));
    dispatch(gesture("gesturechange", 2, ON_SPHERE));
    dispatch(touch("touchstart", fingers(ON_SPHERE, 100)));
    dispatch(touch("touchmove", fingers(ON_SPHERE, 200)));

    expect(camera.altitude()).toBe(START_ALTITUDE);
  });
});

describe("hitsSphere", () => {
  it("переводит экранную точку в макетную через фактический размер холста", () => {
    const { globe, toGlobeCoords } = createGlobe();
    const el = document.createElement("div");
    // An 800x600 canvas drawn in a 1600x1200 rect shifted by (100, 50): scale 2.
    vi.spyOn(el, "getBoundingClientRect").mockReturnValue(new DOMRect(100, 50, 1600, 1200));

    expect(hitsSphere(el, globe, LAYOUT, 900, 650)).toBe(false);
    expect(toGlobeCoords).toHaveBeenLastCalledWith(400, 300);
  });

  it("холст нулевого размера не попадает никуда", () => {
    const { globe, toGlobeCoords } = createGlobe();
    const el = document.createElement("div");

    expect(hitsSphere(el, globe, LAYOUT, 10, 10)).toBe(false);
    expect(toGlobeCoords).not.toHaveBeenCalled();
  });
});

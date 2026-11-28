import { useRef, type ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { stubScreenLayout, type ScreenRect } from "../../test/layout";
import { matchMediaQueries } from "../../test/motion";
import { act, renderWithProviders } from "../../test/render";
import { stubResizeObserver } from "../../test/resizeObserver";
import { useBannerCloseGlide } from "./useBannerCloseGlide";

const DESKTOP_QUERY = "min-width: 62em";
const BANNER_HEIGHT = 52;
const CANVAS_HEIGHT = 600;

/** The stage with what the hook moves (panel, map canvas) and what it must leave (legend). */
function Stage({ children }: { children?: ReactNode }) {
  const stageRef = useRef<HTMLElement>(null);
  useBannerCloseGlide(stageRef);
  return (
    <main ref={stageRef} className="journeys-stage">
      <nav className="journeys-panel" />
      <div className="journeys-map">
        <div className="world-map-canvas" />
      </div>
      <div className="journeys-legend-card" />
      {children}
    </main>
  );
}

interface GlideCall {
  className: string;
  keyframes: Keyframe[];
}

// jsdom has no Web Animations API: the browser boundary the hook drives, recorded per element.
let glides: GlideCall[] = [];
// The stage starts under the banner; a test moves it to emulate the banner closing or opening.
let rects: Record<string, ScreenRect> = {};
let resize: () => void = () => {};

beforeEach(() => {
  glides = [];
  rects = {
    "journeys-stage": { left: 0, top: 90 + BANNER_HEIGHT, width: 1200, height: 700 },
    "world-map-canvas": { left: 0, top: 90 + BANNER_HEIGHT, width: 1000, height: CANVAS_HEIGHT },
  };
  stubScreenLayout(rects);
  resize = stubResizeObserver();
  Element.prototype.animate = vi.fn(function record(this: Element, keyframes: Keyframe[] | PropertyIndexedKeyframes | null) {
    glides.push({ className: this.className, keyframes: keyframes as Keyframe[] });
    return {} as Animation;
  });
});

afterEach(() => {
  // @ts-expect-error -- removing the test's own polyfill; jsdom never had the method
  delete Element.prototype.animate;
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

/** The stage top moves by `shift` (up when positive) and the layout reports a resize. */
function moveStageUp(shift: number): void {
  rects["journeys-stage"] = { ...rects["journeys-stage"], top: rects["journeys-stage"].top - shift };
  act(() => resize());
}

describe("useBannerCloseGlide", () => {
  it("закрытие плашки: панель съезжает вверх со старого места, карта растёт от старой высоты", () => {
    matchMediaQueries(DESKTOP_QUERY);
    renderWithProviders(<Stage />);

    moveStageUp(BANNER_HEIGHT);

    expect(glides).toEqual([
      {
        className: "journeys-panel",
        keyframes: [{ transform: `translateY(${BANNER_HEIGHT}px)` }, { transform: "none" }],
      },
      {
        className: "world-map-canvas",
        keyframes: [
          { transform: `scale(${(CANVAS_HEIGHT - BANNER_HEIGHT) / CANVAS_HEIGHT})`, transformOrigin: "50% 100%" },
          { transform: "none", transformOrigin: "50% 100%" },
        ],
      },
    ]);
  });

  it("перетащенная карточка едет с панелью, карточка в углу стоит, статус карты — на половину сдвига", () => {
    matchMediaQueries(DESKTOP_QUERY);
    renderWithProviders(
      <Stage>
        <section className="movements-controls dragged" style={{ left: 300, top: 40, bottom: "auto" }} />
        <section className="movements-controls cornered" />
        <output className="journeys-map-status" />
      </Stage>,
    );

    moveStageUp(BANNER_HEIGHT);

    const moved = (className: string) => glides.find((glide) => glide.className === className)?.keyframes[0];
    expect(moved("movements-controls dragged")).toEqual({ transform: `translateY(${BANNER_HEIGHT}px)` });
    expect(moved("movements-controls cornered")).toBeUndefined();
    expect(moved("journeys-map-status")).toEqual({ transform: `translateY(${BANNER_HEIGHT / 2}px)` });
  });

  it("появление плашки и ресайз без сдвига не анимируются", () => {
    matchMediaQueries(DESKTOP_QUERY);
    renderWithProviders(<Stage />);

    moveStageUp(-BANNER_HEIGHT);
    moveStageUp(0);

    expect(glides).toEqual([]);
  });

  it.each([
    ["на узком экране", () => matchMediaQueries("nothing matches")],
    ["при «меньше движения»", () => matchMediaQueries(DESKTOP_QUERY, "prefers-reduced-motion")],
  ])("%s закрытие плашки обходится без анимации", (_, setUp) => {
    setUp();
    renderWithProviders(<Stage />);

    moveStageUp(BANNER_HEIGHT);

    expect(glides).toEqual([]);
  });
});

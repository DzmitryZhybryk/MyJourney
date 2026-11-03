import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { EventDispatcher } from "three";
import type { OrbitControls } from "three/addons/controls/OrbitControls.js";

import { GEO_CITIES } from "../../test/handlers";
import { act, renderWithProviders } from "../../test/render";
import { stubResizeObserver } from "../../test/resizeObserver";
import { GlobeCanvas } from "./GlobeCanvas";
import { createGlobeLabel } from "./globeLabel";
import type { GlobeRoute } from "./route";
import type { RouteHtmlDatum, RouteTrail } from "./routeScene";
import type { GlobeCity } from "./routes";

/*
 * The branches of this component open only once the container gets a SIZE: before that `<Globe>`
 * is not mounted, the ref is empty and the camera setup effect exits on its first line. The global
 * ResizeObserver stub from `src/test/setup.ts` never fires its callback, so the test fires it.
 */
let fireResize: ((width: number, height: number) => void) | null = null;

/** The globe.gl instance that the mock returns instead of real three/WebGL. */
let controls: Pick<OrbitControls,
  | "autoRotate" | "autoRotateSpeed" | "enableZoom" | "enablePan" | "enableRotate"
  | "addEventListener" | "removeEventListener" | "dispatchEvent"
>;
const pointOfView = vi.fn();
const pauseAnimation = vi.fn();
const resumeAnimation = vi.fn();
const toGlobeCoords = vi.fn();
// The camera is needed by the label declutterer: the "matrix unchanged, skip the frame" gate.
const cameraStub = { matrixWorld: { elements: [0] } };
// The renderer canvas is needed by the interactive effect (it overrides OrbitControls' touch-action).
const rendererDomElement = document.createElement("canvas");

// Props of the last `<Globe>` render: they show what the canvas feeds the layers (data, accessors).
let globeProps: Record<string, unknown> = {};

vi.mock("react-globe.gl", () => ({
  default: (props: { ref?: { current?: unknown } }) => {
    globeProps = props;
    // globe.gl hands out the imperative instance via ref; reproduce exactly that.
    if (props.ref) {
      props.ref.current = {
        controls: () => controls,
        renderer: () => ({ domElement: rendererDomElement }),
        camera: () => cameraStub,
        pointOfView,
        pauseAnimation,
        resumeAnimation,
        toGlobeCoords,
      };
    }

    return null;
  },
}));

function setReducedMotion(reduced: boolean) {
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches: reduced,
    media: query,
    addEventListener: () => {},
    removeEventListener: () => {},
  }));
}

beforeEach(() => {
  globeProps = {};
  controls = Object.assign(new EventDispatcher(), {
    autoRotate: false, autoRotateSpeed: 0, enableZoom: true, enablePan: true, enableRotate: true,
  });
  // By default "off the sphere": each test sets a hit explicitly.
  toGlobeCoords.mockReturnValue(null);
  cameraStub.matrixWorld.elements = [0];
  fireResize = stubResizeObserver();
  setReducedMotion(false);
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

describe("GlobeCanvas", () => {
  it("не монтирует холст, пока контейнер без размера", () => {
    const { container } = renderWithProviders(<GlobeCanvas />);

    expect(container.querySelector(".globe-canvas")).not.toBeNull();
    expect(pointOfView).not.toHaveBeenCalled();
  });

  it("получив размер, настраивает камеру и глушит зум и пан", () => {
    renderWithProviders(<GlobeCanvas />);

    act(() => fireResize?.(800, 600));

    expect(controls.enableZoom).toBe(false);
    expect(controls.enablePan).toBe(false);
    expect(controls.autoRotate).toBe(true);
    expect(pointOfView).toHaveBeenCalledTimes(1);
  });

  it("первую точку обзора ставит мгновенно, без перелёта", () => {
    renderWithProviders(<GlobeCanvas />);

    act(() => fireResize?.(800, 600));

    // The second argument is the duration: on the first set it must be zero, otherwise the globe
    // would fly in from afar on every page open.
    expect(pointOfView).toHaveBeenLastCalledWith(expect.anything(), 0);
  });

  it("смену точки обзора проигрывает перелётом", () => {
    const { rerender } = renderWithProviders(<GlobeCanvas pov={{ lat: 0, lng: 0, altitude: 2 }} />);

    act(() => fireResize?.(800, 600));
    act(() => rerender(<GlobeCanvas pov={{ lat: 40, lng: 30, altitude: 1.8 }} />));

    expect(pointOfView).toHaveBeenCalledTimes(2);
    expect(pointOfView).toHaveBeenLastCalledWith(expect.anything(), expect.any(Number));
    expect(pointOfView.mock.calls[1]?.[1]).toBeGreaterThan(0);
  });

  it("при prefers-reduced-motion не вращает и не летает", () => {
    setReducedMotion(true);
    const { rerender } = renderWithProviders(<GlobeCanvas pov={{ lat: 0, lng: 0, altitude: 2 }} />);

    act(() => fireResize?.(800, 600));
    act(() => rerender(<GlobeCanvas pov={{ lat: 40, lng: 30, altitude: 1.8 }} />));

    expect(controls.autoRotate).toBe(false);
    // Even a face change is instant: a flight is an animation.
    expect(pointOfView.mock.calls.at(-1)?.[1]).toBe(0);
  });

  it("autoRotate={false} отключает вращение", () => {
    renderWithProviders(<GlobeCanvas autoRotate={false} />);

    act(() => fireResize?.(800, 600));

    expect(controls.autoRotate).toBe(false);
  });

  it("останавливает рендер, когда вкладку скрыли, и возобновляет при возврате", () => {
    renderWithProviders(<GlobeCanvas />);
    act(() => fireResize?.(800, 600));
    // The instance appearing already applied play-state (resume for a non-paused one); from here
    // count ONLY the effect of visibilitychange.
    pauseAnimation.mockClear();
    resumeAnimation.mockClear();

    const setHidden = (hidden: boolean) =>
      Object.defineProperty(document, "hidden", { value: hidden, configurable: true });

    act(() => {
      setHidden(true);
      document.dispatchEvent(new Event("visibilitychange"));
    });
    expect(pauseAnimation).toHaveBeenCalledTimes(1);

    act(() => {
      setHidden(false);
      document.dispatchEvent(new Event("visibilitychange"));
    });
    expect(resumeAnimation).toHaveBeenCalledTimes(1);
  });

  it("paused ставит на паузу инстанс, появившийся уже спрятанным (прямой заход на /journeys)", () => {
    // On the first render the ref is empty (no size); Globe mounts only after measuring. The pause
    // must apply once the instance appears, otherwise the hidden globe's rAF would run.
    renderWithProviders(<GlobeCanvas paused />);

    act(() => fireResize?.(800, 600));

    expect(pauseAnimation).toHaveBeenCalled();
    expect(resumeAnimation).not.toHaveBeenCalled();
  });

  it("нулевой размер не доводит настройку до конца", () => {
    renderWithProviders(<GlobeCanvas />);

    act(() => fireResize?.(0, 0));

    expect(pointOfView).not.toHaveBeenCalled();
  });

  it("interactive: жест на сфере включает вращение, ставит автовращение на паузу и глушит скролл", () => {
    toGlobeCoords.mockReturnValue({ lat: 10, lng: 20 });
    const { container } = renderWithProviders(<GlobeCanvas interactive />);
    act(() => fireResize?.(800, 600));
    const el = container.querySelector<HTMLElement>(".globe-canvas");
    if (!el) throw new Error("контейнер глобуса не отрендерился");
    vi.spyOn(el, "getBoundingClientRect").mockReturnValue(new DOMRect(0, 0, 800, 600));

    act(() => {
      el.dispatchEvent(new MouseEvent("pointerdown", { bubbles: true }));
    });

    expect(controls.enableRotate).toBe(true);
    expect(controls.autoRotate).toBe(false);

    const touchMove = new Event("touchmove", { bubbles: true, cancelable: true });
    act(() => {
      el.dispatchEvent(touchMove);
    });

    expect(touchMove.defaultPrevented).toBe(true);
  });

  it("interactive: жест мимо сферы вращение не включает и скролл не трогает", () => {
    toGlobeCoords.mockReturnValue(null);
    const { container } = renderWithProviders(<GlobeCanvas interactive />);
    act(() => fireResize?.(800, 600));
    const el = container.querySelector<HTMLElement>(".globe-canvas");
    if (!el) throw new Error("контейнер глобуса не отрендерился");
    vi.spyOn(el, "getBoundingClientRect").mockReturnValue(new DOMRect(0, 0, 800, 600));

    act(() => {
      el.dispatchEvent(new MouseEvent("pointerdown", { bubbles: true }));
    });

    expect(controls.enableRotate).toBe(false);
    expect(controls.autoRotate).toBe(true);

    const touchMove = new Event("touchmove", { bubbles: true, cancelable: true });
    act(() => {
      el.dispatchEvent(touchMove);
    });

    expect(touchMove.defaultPrevented).toBe(false);
  });

  it("interactive: отпускание возвращает автовращение с нового места", () => {
    toGlobeCoords.mockReturnValue({ lat: 10, lng: 20 });
    const { container } = renderWithProviders(<GlobeCanvas interactive />);
    act(() => fireResize?.(800, 600));
    const el = container.querySelector<HTMLElement>(".globe-canvas");
    if (!el) throw new Error("контейнер глобуса не отрендерился");
    vi.spyOn(el, "getBoundingClientRect").mockReturnValue(new DOMRect(0, 0, 800, 600));

    act(() => {
      el.dispatchEvent(new MouseEvent("pointerdown", { bubbles: true }));
    });
    expect(controls.autoRotate).toBe(false);

    act(() => {
      window.dispatchEvent(new Event("pointerup"));
    });

    expect(controls.autoRotate).toBe(true);
  });

  it("interactive: второе касание мимо сферы не обрывает драг и не глушит автовращение", () => {
    // The first pointerdown hits the sphere, the second (a finger/palm off the ball) does not.
    toGlobeCoords.mockReturnValueOnce({ lat: 10, lng: 20 });
    const { container } = renderWithProviders(<GlobeCanvas interactive />);
    act(() => fireResize?.(800, 600));
    const el = container.querySelector<HTMLElement>(".globe-canvas");
    if (!el) throw new Error("контейнер глобуса не отрендерился");
    vi.spyOn(el, "getBoundingClientRect").mockReturnValue(new DOMRect(0, 0, 800, 600));

    act(() => {
      el.dispatchEvent(new MouseEvent("pointerdown", { bubbles: true }));
    });
    expect(controls.autoRotate).toBe(false);

    act(() => {
      el.dispatchEvent(new MouseEvent("pointerdown", { bubbles: true }));
    });
    expect(controls.enableRotate).toBe(true);

    act(() => {
      window.dispatchEvent(new Event("pointerup"));
    });

    expect(controls.autoRotate).toBe(true);
  });

  it("interactive: наведение показывает grab-курсор над сферой и снимает его мимо неё", () => {
    const { container } = renderWithProviders(<GlobeCanvas interactive />);
    act(() => fireResize?.(800, 600));
    const el = container.querySelector<HTMLElement>(".globe-canvas");
    if (!el) throw new Error("контейнер глобуса не отрендерился");
    vi.spyOn(el, "getBoundingClientRect").mockReturnValue(new DOMRect(0, 0, 800, 600));

    toGlobeCoords.mockReturnValue({ lat: 10, lng: 20 });
    act(() => {
      el.dispatchEvent(new MouseEvent("pointermove", { bubbles: true }));
    });
    expect(el.style.cursor).toBe("grab");

    toGlobeCoords.mockReturnValue(null);
    act(() => {
      el.dispatchEvent(new MouseEvent("pointermove", { bubbles: true }));
    });
    expect(el.style.cursor).toBe("");
  });

  it("interactive: хит-тест переводит экранные координаты в макетные (scale кадрирования stage)", () => {
    toGlobeCoords.mockReturnValue(null);
    const { container } = renderWithProviders(<GlobeCanvas interactive />);
    act(() => fireResize?.(800, 600));
    const el = container.querySelector<HTMLElement>(".globe-canvas");
    if (!el) throw new Error("контейнер глобуса не отрендерился");
    // An 800x600 canvas is drawn in a 1600x1200 rect (scale 2): the screen point (800, 600) is layout (400, 300).
    vi.spyOn(el, "getBoundingClientRect").mockReturnValue(new DOMRect(0, 0, 1600, 1200));

    act(() => {
      el.dispatchEvent(new MouseEvent("pointermove", { bubbles: true, clientX: 800, clientY: 600 }));
    });

    expect(toGlobeCoords).toHaveBeenCalledWith(400, 300);
  });

  it("без interactive жесты по канвасу не хит-тестятся вовсе", () => {
    const { container } = renderWithProviders(<GlobeCanvas />);
    act(() => fireResize?.(800, 600));
    const el = container.querySelector<HTMLElement>(".globe-canvas");
    if (!el) throw new Error("контейнер глобуса не отрендерился");

    act(() => {
      el.dispatchEvent(new MouseEvent("pointerdown", { bubbles: true }));
    });

    expect(toGlobeCoords).not.toHaveBeenCalled();
  });

  it("деклаттер: у пересёкшихся подписей гаснет текст дальней от центра, точка остаётся", () => {
    vi.useFakeTimers();
    const { container } = renderWithProviders(
      <GlobeCanvas
        labelCities={[
          { name: "Ташкент", lat: 41.3, lng: 69.2 },
          { name: "Бишкек", lat: 42.9, lng: 74.6 },
        ]}
      />,
    );
    act(() => fireResize?.(800, 600));
    const el = container.querySelector<HTMLElement>(".globe-canvas");
    if (!el) throw new Error("контейнер глобуса не отрендерился");
    vi.spyOn(el, "getBoundingClientRect").mockReturnValue(new DOMRect(0, 0, 800, 600));

    // Build the label layer by hand: the react-globe.gl mock does not render data DOM elements.
    const tashkent = createGlobeLabel("Ташкент", "Ташкент|41.3|69.2");
    const bishkek = createGlobeLabel("Бишкек", "Бишкек|42.9|74.6");
    for (const wrapper of [tashkent, bishkek]) {
      wrapper.style.opacity = "1";
      el.append(wrapper);
    }

    const tashkentName = tashkent.querySelector<HTMLElement>(".globe-label__name");
    const bishkekName = bishkek.querySelector<HTMLElement>(".globe-label__name");
    if (!tashkentName || !bishkekName) throw new Error("подписи не собрались");
    // Disk center (400, 300): Bishkek is closer, Tashkent overlaps it from the side.
    vi.spyOn(tashkentName, "getBoundingClientRect").mockReturnValue(new DOMRect(350, 296, 60, 12));
    vi.spyOn(bishkekName, "getBoundingClientRect").mockReturnValue(new DOMRect(390, 294, 60, 12));

    act(() => {
      vi.advanceTimersByTime(400);
    });

    expect(tashkent.classList.contains("globe-label--decluttered")).toBe(true);
    expect(bishkek.classList.contains("globe-label--decluttered")).toBe(false);
    // The occlusion channel is untouched: the wrapper (and the dot) stays visible, only the text hides.
    expect(tashkent.style.opacity).toBe("1");
  });

  it("деклаттер: пересчёт только при движении камеры; разъезд возвращает текст", () => {
    vi.useFakeTimers();
    const { container } = renderWithProviders(
      <GlobeCanvas
        labelCities={[
          { name: "Ташкент", lat: 41.3, lng: 69.2 },
          { name: "Бишкек", lat: 42.9, lng: 74.6 },
        ]}
      />,
    );
    act(() => fireResize?.(800, 600));
    const el = container.querySelector<HTMLElement>(".globe-canvas");
    if (!el) throw new Error("контейнер глобуса не отрендерился");
    vi.spyOn(el, "getBoundingClientRect").mockReturnValue(new DOMRect(0, 0, 800, 600));

    const tashkent = createGlobeLabel("Ташкент", "Ташкент|41.3|69.2");
    const bishkek = createGlobeLabel("Бишкек", "Бишкек|42.9|74.6");
    for (const wrapper of [tashkent, bishkek]) {
      wrapper.style.opacity = "1";
      el.append(wrapper);
    }

    const tashkentName = tashkent.querySelector<HTMLElement>(".globe-label__name");
    const bishkekName = bishkek.querySelector<HTMLElement>(".globe-label__name");
    if (!tashkentName || !bishkekName) throw new Error("подписи не собрались");
    vi.spyOn(tashkentName, "getBoundingClientRect").mockReturnValue(new DOMRect(350, 296, 60, 12));
    vi.spyOn(bishkekName, "getBoundingClientRect").mockReturnValue(new DOMRect(390, 294, 60, 12));

    act(() => {
      vi.advanceTimersByTime(400);
    });
    expect(tashkent.classList.contains("globe-label--decluttered")).toBe(true);

    // The labels moved apart but the camera did not move: no recompute, the class stays.
    vi.spyOn(tashkentName, "getBoundingClientRect").mockReturnValue(new DOMRect(600, 400, 60, 12));
    act(() => {
      vi.advanceTimersByTime(400);
    });
    expect(tashkent.classList.contains("globe-label--decluttered")).toBe(true);

    // The camera moved: the recompute returns the text (the gap exceeds the hysteresis margin).
    cameraStub.matrixWorld.elements = [1];
    act(() => {
      vi.advanceTimersByTime(400);
    });
    expect(tashkent.classList.contains("globe-label--decluttered")).toBe(false);
  });

  it("деклаттер: остановка эффекта снимает классы — текст не остаётся спрятанным", () => {
    vi.useFakeTimers();
    const { container, unmount } = renderWithProviders(
      <GlobeCanvas
        labelCities={[
          { name: "Ташкент", lat: 41.3, lng: 69.2 },
          { name: "Бишкек", lat: 42.9, lng: 74.6 },
        ]}
      />,
    );
    act(() => fireResize?.(800, 600));
    const el = container.querySelector<HTMLElement>(".globe-canvas");
    if (!el) throw new Error("контейнер глобуса не отрендерился");
    vi.spyOn(el, "getBoundingClientRect").mockReturnValue(new DOMRect(0, 0, 800, 600));

    const tashkent = createGlobeLabel("Ташкент", "Ташкент|41.3|69.2");
    const bishkek = createGlobeLabel("Бишкек", "Бишкек|42.9|74.6");
    for (const wrapper of [tashkent, bishkek]) {
      wrapper.style.opacity = "1";
      el.append(wrapper);
    }

    const tashkentName = tashkent.querySelector<HTMLElement>(".globe-label__name");
    const bishkekName = bishkek.querySelector<HTMLElement>(".globe-label__name");
    if (!tashkentName || !bishkekName) throw new Error("подписи не собрались");
    vi.spyOn(tashkentName, "getBoundingClientRect").mockReturnValue(new DOMRect(350, 296, 60, 12));
    vi.spyOn(bishkekName, "getBoundingClientRect").mockReturnValue(new DOMRect(390, 294, 60, 12));

    act(() => {
      vi.advanceTimersByTime(400);
    });
    expect(tashkent.classList.contains("globe-label--decluttered")).toBe(true);

    unmount();

    expect(tashkent.classList.contains("globe-label--decluttered")).toBe(false);
  });

  it("деклаттер: скрытая окклюзией подпись не участвует в расчёте", () => {
    vi.useFakeTimers();
    const { container } = renderWithProviders(
      <GlobeCanvas
        labelCities={[
          { name: "Ташкент", lat: 41.3, lng: 69.2 },
          { name: "Бишкек", lat: 42.9, lng: 74.6 },
        ]}
      />,
    );
    act(() => fireResize?.(800, 600));
    const el = container.querySelector<HTMLElement>(".globe-canvas");
    if (!el) throw new Error("контейнер глобуса не отрендерился");
    vi.spyOn(el, "getBoundingClientRect").mockReturnValue(new DOMRect(0, 0, 800, 600));

    const tashkent = createGlobeLabel("Ташкент", "Ташкент|41.3|69.2");
    const bishkek = createGlobeLabel("Бишкек", "Бишкек|42.9|74.6");
    tashkent.style.opacity = "1";
    // Bishkek went behind the horizon: occlusion hid the whole wrapper.
    bishkek.style.opacity = "0";
    el.append(tashkent, bishkek);

    const tashkentName = tashkent.querySelector<HTMLElement>(".globe-label__name");
    const bishkekName = bishkek.querySelector<HTMLElement>(".globe-label__name");
    if (!tashkentName || !bishkekName) throw new Error("подписи не собрались");
    vi.spyOn(tashkentName, "getBoundingClientRect").mockReturnValue(new DOMRect(350, 296, 60, 12));
    vi.spyOn(bishkekName, "getBoundingClientRect").mockReturnValue(new DOMRect(390, 294, 60, 12));

    act(() => {
      vi.advanceTimersByTime(400);
    });

    expect(tashkent.classList.contains("globe-label--decluttered")).toBe(false);
    expect(bishkek.classList.contains("globe-label--decluttered")).toBe(false);
  });
});

describe("GlobeCanvas — маршрут формы поездки", () => {
  const [MOSCOW, LONDON] = GEO_CITIES;
  const CITIES: GlobeCity[] = [{ name: "Minsk", lat: 53.9, lng: 27.56 }];

  function makeRoute(overrides: Partial<GlobeRoute> = {}): GlobeRoute {
    return {
      origin: MOSCOW,
      destination: LONDON,
      transportType: "air",
      originLabel: "Moscow",
      destinationLabel: "London",
      ...overrides,
    };
  }

  function htmlData(): object[] {
    return globeProps.htmlElementsData as object[];
  }

  function routeData(): RouteHtmlDatum[] {
    return htmlData().filter((datum): datum is RouteHtmlDatum => "kind" in datum);
  }

  beforeEach(() => {
    // Without animation the vehicle stands at the end of the path at once: the position is deterministic.
    setReducedMotion(true);
  });

  it("без маршрута отдаёт слою подписей тот же массив городов — слой не пересобирается", () => {
    renderWithProviders(<GlobeCanvas labelCities={CITIES} />);
    act(() => fireResize?.(800, 600));

    expect(htmlData()).toBe(CITIES);
    expect(globeProps.pathsData).toEqual([]);
  });

  it("полный маршрут: пины обоих концов, транспорт в конце пути и след", () => {
    renderWithProviders(<GlobeCanvas route={makeRoute()} />);
    act(() => fireResize?.(800, 600));

    const pins = routeData().filter((datum) => datum.kind === "route-pin");
    const vehicle = routeData().find((datum) => datum.kind === "route-vehicle");

    expect(pins.map((pin) => pin.name)).toEqual(["Moscow", "London"]);
    expect(vehicle?.lat).toBeCloseTo(LONDON.latitude);
    expect(vehicle?.lng).toBeCloseTo(LONDON.longitude);
    expect(globeProps.pathsData).toHaveLength(1);
  });

  it("выбран один город — только его пин, без транспорта и следа", () => {
    renderWithProviders(<GlobeCanvas route={makeRoute({ destination: null, transportType: null })} />);
    act(() => fireResize?.(800, 600));

    expect(routeData()).toEqual([expect.objectContaining({ kind: "route-pin", name: "Moscow" })]);
    expect(globeProps.pathsData).toEqual([]);
  });

  it("оба города без среды передвижения — пины без следа и транспорта", () => {
    renderWithProviders(<GlobeCanvas route={makeRoute({ transportType: null })} />);
    act(() => fireResize?.(800, 600));

    expect(routeData().map((datum) => datum.kind)).toEqual(["route-pin", "route-pin"]);
    expect(globeProps.pathsData).toEqual([]);
  });

  it("подписи городов и маршрут делят один html-слой", () => {
    renderWithProviders(<GlobeCanvas labelCities={CITIES} route={makeRoute()} />);
    act(() => fireResize?.(800, 600));

    expect(htmlData()).toEqual(expect.arrayContaining([CITIES[0], expect.objectContaining({ kind: "route-pin" })]));
  });

  it("аксессоры различают подпись и элемент маршрута: высота и DOM", () => {
    renderWithProviders(<GlobeCanvas labelCities={CITIES} route={makeRoute()} />);
    act(() => fireResize?.(800, 600));
    const altitude = globeProps.htmlAltitude as (datum: object) => number;
    const element = globeProps.htmlElement as (datum: object) => HTMLElement;
    const [pin] = routeData();

    expect(altitude(CITIES[0])).toBe(0);
    expect(altitude(pin)).toBeGreaterThan(0);
    expect(element(CITIES[0]).classList.contains("globe-label")).toBe(true);
    expect(element(pin).classList.contains("globe-route-pin")).toBe(true);
    expect(element(pin).textContent).toBe("Moscow");
  });

  it("окклюзия: подпись гаснет прозрачностью, элемент маршрута прячется, не трогая opacity", () => {
    renderWithProviders(<GlobeCanvas labelCities={CITIES} route={makeRoute()} />);
    act(() => fireResize?.(800, 600));
    const element = globeProps.htmlElement as (datum: object) => HTMLElement;
    const hideBehindGlobe = globeProps.htmlElementVisibilityModifier as (el: HTMLElement, visible: boolean) => void;
    const label = element(CITIES[0]);
    const pin = element(routeData()[0]);

    hideBehindGlobe(label, false);
    hideBehindGlobe(pin, false);

    expect(label.style.opacity).toBe("0");
    expect(pin.style.visibility).toBe("hidden");
    // The pin's opacity is free for the route fade-out: occlusion does not take it.
    expect(pin.style.opacity).toBe("");

    hideBehindGlobe(pin, true);
    expect(pin.style.visibility).toBe("");
  });

  it("позиции html-меток ставятся без твина — иначе транспорт отставал бы от следа", () => {
    renderWithProviders(<GlobeCanvas route={makeRoute()} />);
    act(() => fireResize?.(800, 600));

    expect(globeProps.htmlTransitionDuration).toBe(0);
  });

  it("след рисуется непрозрачным закатным цветом, пока маршрут не гаснет", () => {
    renderWithProviders(<GlobeCanvas route={makeRoute()} />);
    act(() => fireResize?.(800, 600));
    const color = globeProps.pathColor as (trail: object) => string;
    const [trail] = globeProps.pathsData as RouteTrail[];

    expect(color(trail)).toBe("rgba(232, 147, 92, 1)");
  });

  it("угасание маршрута помечает контейнер — CSS гасит пины и иконку", () => {
    const { container, rerender } = renderWithProviders(<GlobeCanvas route={makeRoute()} />);
    const canvas = container.querySelector(".globe-canvas");

    expect(canvas?.classList.contains("globe-canvas--route-fading")).toBe(false);

    rerender(<GlobeCanvas route={makeRoute()} routeFading />);
    expect(canvas?.classList.contains("globe-canvas--route-fading")).toBe(true);
  });
});

describe("GlobeCanvas — камера и пауза", () => {
  it("pov, сменившийся вместе с уходом в паузу, ставится без перелёта — спрятанному лететь незачем", () => {
    const { rerender } = renderWithProviders(<GlobeCanvas pov={{ lat: 0, lng: 0, altitude: 2 }} />);
    act(() => fireResize?.(800, 600));

    act(() => rerender(<GlobeCanvas paused pov={{ lat: 40, lng: 30, altitude: 1.8 }} />));

    expect(pointOfView.mock.calls.at(-1)?.[1]).toBe(0);
  });

  it("выход из паузы с новым pov — без перелёта (проявление на месте), следующая смена — перелётом", () => {
    const { rerender } = renderWithProviders(<GlobeCanvas paused pov={{ lat: 0, lng: 0, altitude: 2 }} />);
    act(() => fireResize?.(800, 600));

    act(() => rerender(<GlobeCanvas pov={{ lat: 40, lng: 30, altitude: 1.8 }} />));
    expect(pointOfView.mock.calls.at(-1)?.[1]).toBe(0);

    act(() => rerender(<GlobeCanvas pov={{ lat: 10, lng: 60, altitude: 1.5 }} />));
    expect(pointOfView.mock.calls.at(-1)?.[1]).toBeGreaterThan(0);
  });
});

describe("GlobeCanvas — подлёт камеры при появлении (reveal)", () => {
  const TARGET = { lat: 12, lng: 0, altitude: 2.4 };

  beforeEach(() => {
    vi.useFakeTimers({ toFake: ["requestAnimationFrame", "cancelAnimationFrame", "performance"] });
  });

  type Pov = { lat: number; lng: number; altitude: number };
  function calls(): [Pov, number][] {
    return pointOfView.mock.calls as [Pov, number][];
  }

  it("выход из паузы: камера стартует издалека и покадрово подлетает ровно в pov", () => {
    const { rerender } = renderWithProviders(<GlobeCanvas paused pov={TARGET} reveal />);
    act(() => fireResize?.(800, 600));
    pointOfView.mockClear();

    act(() => rerender(<GlobeCanvas pov={TARGET} reveal />));
    const [start] = calls()[0];
    act(() => vi.advanceTimersByTime(2000));

    expect(start.altitude).toBeGreaterThan(TARGET.altitude);
    // Frames run without the globe.gl tween (duration 0), otherwise it would swallow auto-rotation.
    expect(calls().every(([, duration]) => duration === 0)).toBe(true);
    expect(calls().length).toBeGreaterThan(10);
    const [end] = calls().at(-1) ?? [];
    expect(end?.altitude).toBeCloseTo(TARGET.altitude);
    expect(end?.lng).toBeCloseTo(TARGET.lng);
  });

  it("после подлёта кадры прекращаются — дальше крутит автовращение", () => {
    renderWithProviders(<GlobeCanvas pov={TARGET} reveal />);
    act(() => fireResize?.(800, 600));
    act(() => vi.advanceTimersByTime(2000));
    const settled = pointOfView.mock.calls.length;

    act(() => vi.advanceTimersByTime(1000));

    expect(pointOfView.mock.calls.length).toBe(settled);
  });

  it("захват сферы прерывает подлёт, размонтирование отписывает обработчик", () => {
    const { unmount } = renderWithProviders(<GlobeCanvas pov={TARGET} reveal interactive />);
    act(() => fireResize?.(800, 600));
    const [start] = calls()[0];
    act(() => vi.advanceTimersByTime(300));
    const [inFlight] = calls().at(-1) ?? [];

    expect(inFlight?.altitude).toBeLessThan(start.altitude);
    expect(inFlight?.altitude).toBeGreaterThan(TARGET.altitude);
    act(() => controls.dispatchEvent({ type: "start" }));
    pointOfView.mockClear();
    act(() => vi.advanceTimersByTime(2000));

    expect(pointOfView).not.toHaveBeenCalled();
    unmount();
    // A leaked subscription would cancel the old frame even after unmount.
    const cancelFrame = vi.spyOn(window, "cancelAnimationFrame");
    act(() => controls.dispatchEvent({ type: "start" }));
    expect(cancelFrame).not.toHaveBeenCalled();
  });

  it("щипок над сферой прерывает подлёт — кадры не перетирают выбранную высоту", () => {
    pointOfView.mockImplementation((pov?: Pov) => (pov ? undefined : TARGET));
    toGlobeCoords.mockReturnValue({ lat: 10, lng: 20 });
    const { container } = renderWithProviders(<GlobeCanvas pov={TARGET} reveal interactive />);
    act(() => fireResize?.(800, 600));
    const el = container.querySelector<HTMLElement>(".globe-canvas");
    if (!el) throw new Error("контейнер глобуса не отрендерился");
    vi.spyOn(el, "getBoundingClientRect").mockReturnValue(new DOMRect(0, 0, 800, 600));
    act(() => vi.advanceTimersByTime(300));

    act(() => {
      el.dispatchEvent(new WheelEvent("wheel", { bubbles: true, cancelable: true, ctrlKey: true, deltaY: -20 }));
    });
    const [zoomed] = calls().at(-1) ?? [];
    act(() => vi.advanceTimersByTime(2000));

    expect(calls().at(-1)?.[0]).toBe(zoomed);
  });

  it("смена pov у уже видимого глобуса — обычный перелёт, без повторного подлёта", () => {
    const { rerender } = renderWithProviders(<GlobeCanvas pov={TARGET} reveal />);
    act(() => fireResize?.(800, 600));
    act(() => vi.advanceTimersByTime(2000));
    pointOfView.mockClear();

    const next = { lat: 50, lng: 30, altitude: 1.2 };
    act(() => rerender(<GlobeCanvas pov={next} reveal />));

    expect(calls()).toEqual([[next, expect.any(Number)]]);
    expect(calls()[0]?.[1]).toBeGreaterThan(0);
  });

  it("смена pov посреди подлёта отменяет его — кадры подлёта больше не перетирают камеру", () => {
    const { rerender } = renderWithProviders(<GlobeCanvas pov={TARGET} reveal />);
    act(() => fireResize?.(800, 600));
    act(() => vi.advanceTimersByTime(300));

    const next = { lat: 50, lng: 30, altitude: 1.2 };
    act(() => rerender(<GlobeCanvas pov={next} reveal />));
    pointOfView.mockClear();
    act(() => vi.advanceTimersByTime(2000));

    expect(pointOfView).not.toHaveBeenCalled();
  });

  it("на паузе подлёта нет — спрятанный глобус камеру не гоняет", () => {
    renderWithProviders(<GlobeCanvas paused pov={TARGET} reveal />);

    act(() => fireResize?.(800, 600));

    expect(calls()).toEqual([[TARGET, 0]]);
  });

  it("при prefers-reduced-motion появление мгновенное", () => {
    setReducedMotion(true);
    renderWithProviders(<GlobeCanvas pov={TARGET} reveal />);

    act(() => fireResize?.(800, 600));
    act(() => vi.advanceTimersByTime(2000));

    expect(calls()).toEqual([[TARGET, 0]]);
  });

  it("без reveal появление мгновенное, как на остальных гранях", () => {
    renderWithProviders(<GlobeCanvas pov={TARGET} />);

    act(() => fireResize?.(800, 600));
    act(() => vi.advanceTimersByTime(2000));

    expect(calls()).toEqual([[TARGET, 0]]);
  });
});

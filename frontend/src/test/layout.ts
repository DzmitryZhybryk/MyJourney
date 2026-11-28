import { vi } from "vitest";

/** Element rectangle on screen, px. */
export interface ScreenRect {
  left: number;
  top: number;
  width: number;
  height: number;
}

/** Element layout sizes (`offset*`) and the class of its `offsetParent`. */
export interface OffsetBox {
  /** Without them the position comes from the inline `left`/`top` style, which dragging sets. */
  left?: number;
  top?: number;
  width: number;
  height: number;
  /** Class of the nearest ancestor the element is positioned against. */
  parentClass?: string;
}

function offsetBoxOf(element: Element, boxesByClass: Readonly<Record<string, OffsetBox>>): OffsetBox | undefined {
  return Object.entries(boxesByClass).find(([className]) => element.classList.contains(className))?.[1];
}

/**
 * Sets `offset*` / `client*` layout on elements by CSS class: jsdom has none (everything has zero
 * size and `offsetParent === null`). `clientWidth`/`clientHeight` equal the box size.
 * Undone by `vi.restoreAllMocks()`.
 */
export function stubOffsetLayout(boxesByClass: Readonly<Record<string, OffsetBox>>): void {
  const position = (element: HTMLElement, side: "left" | "top"): number =>
    offsetBoxOf(element, boxesByClass)?.[side] ?? (Number.parseFloat(element.style[side]) || 0);
  const size = (element: HTMLElement, side: "width" | "height"): number =>
    offsetBoxOf(element, boxesByClass)?.[side] ?? 0;

  vi.spyOn(HTMLElement.prototype, "offsetParent", "get").mockImplementation(function parentOf(this: HTMLElement) {
    const parentClass = offsetBoxOf(this, boxesByClass)?.parentClass;
    return parentClass ? this.closest(`.${parentClass}`) : null;
  });
  vi.spyOn(HTMLElement.prototype, "offsetLeft", "get").mockImplementation(function leftOf(this: HTMLElement) {
    return position(this, "left");
  });
  vi.spyOn(HTMLElement.prototype, "offsetTop", "get").mockImplementation(function topOf(this: HTMLElement) {
    return position(this, "top");
  });
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockImplementation(function widthOf(this: HTMLElement) {
    return size(this, "width");
  });
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockImplementation(function heightOf(this: HTMLElement) {
    return size(this, "height");
  });
  vi.spyOn(Element.prototype, "clientWidth", "get").mockImplementation(function clientWidthOf(this: Element) {
    return this instanceof HTMLElement ? size(this, "width") : 0;
  });
  vi.spyOn(Element.prototype, "clientHeight", "get").mockImplementation(function clientHeightOf(this: Element) {
    return this instanceof HTMLElement ? size(this, "height") : 0;
  });
}

/**
 * Sets screen rectangles on elements by CSS class: jsdom has no layout and `getBoundingClientRect`
 * returns zeros for all. An element whose class is not in the map is zero.
 * Undone by `vi.restoreAllMocks()`.
 */
export function stubScreenLayout(rectsByClass: Readonly<Record<string, ScreenRect>>): void {
  vi.spyOn(Element.prototype, "getBoundingClientRect").mockImplementation(function rectOf(this: Element) {
    const known = Object.entries(rectsByClass).find(([className]) => this.classList.contains(className))?.[1];
    const { left, top, width, height } = known ?? { left: 0, top: 0, width: 0, height: 0 };
    return DOMRect.fromRect({ x: left, y: top, width, height });
  });
}

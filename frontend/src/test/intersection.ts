/**
 * A controllable `IntersectionObserver` for jsdom (it has none): installed globally in
 * `setup.ts`, and the test decides when observed elements "appear on screen".
 */

const liveObservers = new Set<IntersectionObserverStub>();

export class IntersectionObserverStub {
  readonly root = null;
  readonly rootMargin = "";
  readonly thresholds: readonly number[] = [];
  private readonly targets = new Set<Element>();
  private readonly callback: IntersectionObserverCallback;

  constructor(callback: IntersectionObserverCallback) {
    this.callback = callback;
    liveObservers.add(this);
  }

  observe(target: Element): void {
    this.targets.add(target);
  }

  unobserve(target: Element): void {
    this.targets.delete(target);
  }

  disconnect(): void {
    this.targets.clear();
    liveObservers.delete(this);
  }

  takeRecords(): IntersectionObserverEntry[] {
    return [];
  }

  /** Reports an entry for the element to the observer if it observes it. */
  report(target: Element, entry: Partial<IntersectionObserverEntry>): void {
    if (this.targets.has(target)) {
      this.callback([{ target, ...entry } as IntersectionObserverEntry], this as unknown as IntersectionObserver);
    }
  }

  /** Tells the observer that all its elements are on screen. */
  intersectAll(): void {
    const entries = [...this.targets].map(
      (target) => ({ target, isIntersecting: true, intersectionRatio: 1 }) as IntersectionObserverEntry,
    );
    if (entries.length > 0) {
      this.callback(entries, this as unknown as IntersectionObserver);
    }
  }
}

/**
 * "Scrolls" to every observed element: all live observers get an intersection. Call inside `act`
 * if the callback changes state.
 */
export function intersectAllObserved(): void {
  for (const observer of liveObservers) {
    observer.intersectAll();
  }
}

/**
 * Reports the given entry to everyone observing the element: the element's and the root's
 * position and the visible share. Call inside `act` if the callback changes state.
 */
export function reportIntersection(target: Element, entry: Partial<IntersectionObserverEntry>): void {
  for (const observer of liveObservers) {
    observer.report(target, entry);
  }
}

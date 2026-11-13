import { vi } from "vitest";

/**
 * Replaces the never-firing `ResizeObserver` stub from `setup.ts` with one the test fires itself.
 * Returns the trigger: it calls every connected observer with the given content size. Undone by
 * `vi.unstubAllGlobals()`.
 */
export function stubResizeObserver(): (width?: number, height?: number) => void {
  const connected = new Set<ControllableResizeObserver>();

  class ControllableResizeObserver {
    // A field, not a parameter property: `erasableSyntaxOnly` rejects `constructor(private ...)`.
    callback: ResizeObserverCallback;

    constructor(callback: ResizeObserverCallback) {
      this.callback = callback;
      connected.add(this);
    }
    observe(): void {}
    unobserve(): void {}
    disconnect(): void {
      connected.delete(this);
    }
  }

  vi.stubGlobal("ResizeObserver", ControllableResizeObserver);
  return (width = 0, height = 0) => {
    for (const observer of connected) {
      observer.callback(
        [{ contentRect: { width, height } } as unknown as ResizeObserverEntry],
        observer as unknown as ResizeObserver,
      );
    }
  };
}

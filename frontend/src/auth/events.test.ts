import { afterEach, describe, expect, it, vi } from "vitest";

import { emit, on } from "./events";

describe("auth events", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("вызывает подписчика при emit того же события", () => {
    const listener = vi.fn();
    const off = on("auth-required", listener);

    emit("auth-required", undefined);

    expect(listener).toHaveBeenCalledTimes(1);
    off();
  });

  it("не вызывает подписчика после отписки", () => {
    const listener = vi.fn();
    const off = on("auth-required", listener);

    off();
    emit("auth-required", undefined);

    expect(listener).not.toHaveBeenCalled();
  });

  it("доставляет событие всем подписчикам", () => {
    const first = vi.fn();
    const second = vi.fn();
    const offFirst = on("auth-required", first);
    const offSecond = on("auth-required", second);

    emit("auth-required", undefined);

    expect(first).toHaveBeenCalledTimes(1);
    expect(second).toHaveBeenCalledTimes(1);
    offFirst();
    offSecond();
  });
});

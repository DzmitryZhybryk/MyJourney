import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { readControlsPosition, saveControlsPosition } from "./controlsPosition";

describe("controlsPosition", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("сохранённое положение переживает перечитывание", () => {
    saveControlsPosition({ left: 340, top: 520 });

    expect(readControlsPosition()).toEqual({ left: 340, top: 520 });
  });

  it("сброс забывает положение — карточка вернётся в угол по умолчанию", () => {
    saveControlsPosition({ left: 340, top: 520 });
    saveControlsPosition(null);

    expect(readControlsPosition()).toBeNull();
  });

  it("испорченная запись читается как «не сохранено»", () => {
    localStorage.setItem("journeys-movements-controls-position", "{not json");
    expect(readControlsPosition()).toBeNull();

    localStorage.setItem("journeys-movements-controls-position", JSON.stringify({ left: "a", top: 1 }));
    expect(readControlsPosition()).toBeNull();
  });

  it("недоступный localStorage не ломает карточку: читается как «не сохранено», запись молча пропускается", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("SecurityError");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("QuotaExceededError");
    });

    expect(readControlsPosition()).toBeNull();
    expect(() => saveControlsPosition({ left: 1, top: 2 })).not.toThrow();
  });
});

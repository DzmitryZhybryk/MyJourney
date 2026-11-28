import { describe, expect, it } from "vitest";

import { breakStorage } from "../../test/storage";
import { isLegendCollapsed, setLegendCollapsed } from "./legendStorage";

const KEY = "journeys-legend-collapsed";

describe("legendStorage", () => {
  it("по умолчанию (ничего не сохранено) легенда не свёрнута", () => {
    expect(isLegendCollapsed()).toBe(false);
  });

  it("читает свёрнутое состояние из сохранённого флага", () => {
    localStorage.setItem(KEY, "1");
    expect(isLegendCollapsed()).toBe(true);
  });

  it("любое значение кроме \"1\" считается развёрнутым", () => {
    localStorage.setItem(KEY, "0");
    expect(isLegendCollapsed()).toBe(false);
  });

  it("setLegendCollapsed(true) записывает флаг в localStorage", () => {
    setLegendCollapsed(true);
    expect(localStorage.getItem(KEY)).toBe("1");
    expect(isLegendCollapsed()).toBe(true);
  });

  it("setLegendCollapsed(false) очищает флаг", () => {
    localStorage.setItem(KEY, "1");
    setLegendCollapsed(false);
    expect(localStorage.getItem(KEY)).toBeNull();
    expect(isLegendCollapsed()).toBe(false);
  });

  it("недоступный localStorage при чтении → false (без исключения)", () => {
    breakStorage("getItem");
    expect(isLegendCollapsed()).toBe(false);
  });

  it("недоступный localStorage при записи → тихо проглатываем", () => {
    breakStorage("setItem");
    expect(() => setLegendCollapsed(true)).not.toThrow();
  });
});

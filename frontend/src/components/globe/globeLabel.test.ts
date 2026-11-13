import { describe, expect, it } from "vitest";

import { applyLabelVisibility, createGlobeLabel } from "./globeLabel";

describe("createGlobeLabel", () => {
  it("собирает обёртку с точкой, названием и ключом деклаттера", () => {
    const label = createGlobeLabel("Reykjavík", "Reykjavík|64.1|-21.9");

    expect(label.className).toBe("globe-label");
    expect(label.querySelector(".globe-label__dot")).not.toBeNull();
    expect(label.querySelector(".globe-label__name")?.textContent).toBe("Reykjavík");
    expect(label.dataset.labelId).toBe("Reykjavík|64.1|-21.9");
  });

  it("вставляет название текстом, а не разметкой", () => {
    // The key guarantee: labels come from data, and an HTML string instead of textContent would make
    // them an XSS vector. This is what is checked, not the look.
    const label = createGlobeLabel("<img src=x onerror=alert(1)>", "xss|0|0");

    expect(label.querySelector("img")).toBeNull();
    expect(label.querySelector(".globe-label__name")?.textContent).toBe(
      "<img src=x onerror=alert(1)>",
    );
  });

  it("не падает на пустом названии", () => {
    expect(createGlobeLabel("", "пусто|0|0").querySelector(".globe-label__name")?.textContent).toBe("");
  });

  it("без названия — только точка, без подписи", () => {
    const label = createGlobeLabel(undefined, "|0|0");

    expect(label.querySelector(".globe-label__dot")).not.toBeNull();
    expect(label.querySelector(".globe-label__name")).toBeNull();
  });
});

describe("applyLabelVisibility", () => {
  it("гасит метку на дальней стороне и возвращает на ближней", () => {
    const label = createGlobeLabel("Lisboa", "Lisboa|38.7|-9.1");

    applyLabelVisibility(label, false);
    expect(label.style.opacity).toBe("0");

    applyLabelVisibility(label, true);
    expect(label.style.opacity).toBe("1");
  });
});

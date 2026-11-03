import { describe, expect, it } from "vitest";

import { toApiLanguage } from "./apiLanguage";

describe("toApiLanguage", () => {
  it("русский интерфейс, в том числе региональный вариант, просит русские названия", () => {
    expect(toApiLanguage("ru")).toBe("ru");
    expect(toApiLanguage("ru-RU")).toBe("ru");
  });

  it("любой другой язык просит английские названия", () => {
    expect(toApiLanguage("en")).toBe("en");
    expect(toApiLanguage("en-GB")).toBe("en");
    expect(toApiLanguage("de")).toBe("en");
  });
});

import { describe, expect, it } from "vitest";

import { renderWithProviders, waitFor } from "../test/render";
import { DocumentTitle } from "./DocumentTitle";

/** Renders the component at a route and waits until it sets the title. */
async function titleAt(route: string): Promise<string> {
  renderWithProviders(<DocumentTitle />, { route });
  await waitFor(() => expect(document.title).not.toBe(""));
  return document.title;
}

describe("DocumentTitle", () => {
  it("на лендинге ставит полный заголовок с оффером", async () => {
    // The root has no "section", so the branch with the brand first applies.
    expect(await titleAt("/")).toMatch(/^MyJourney — /u);
  });

  it("на /login ставит «раздел · бренд»", async () => {
    expect(await titleAt("/login")).toBe("Welcome back · MyJourney");
  });

  it("на /signup ставит «раздел · бренд»", async () => {
    expect(await titleAt("/signup")).toBe("Create account · MyJourney");
  });

  it("на /home ставит «раздел · бренд»", async () => {
    expect(await titleAt("/home")).toBe("Home · MyJourney");
  });

  it("на /journeys ставит заголовок раздела", async () => {
    expect(await titleAt("/journeys")).toBe("Journeys · MyJourney");
  });

  it("для /journeys/add берёт заголовок формы, а не раздела", async () => {
    // Branch order matters: /journeys/add starts with /journeys, and with the checks reversed the
    // form would get the section title.
    expect(await titleAt("/journeys/add")).toBe("New journey · MyJourney");
  });

  it("на неизвестном пути откатывается к заголовку лендинга", async () => {
    expect(await titleAt("/nope")).toMatch(/^MyJourney — /u);
  });
});

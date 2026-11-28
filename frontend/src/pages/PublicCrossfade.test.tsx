import { describe, expect, it } from "vitest";
import { Link, Route, Routes } from "react-router";

import { renderWithProviders, screen, waitFor } from "../test/render";
import { PublicCrossfade } from "./PublicCrossfade";

/**
 * The public zone in miniature: a layout with a cross-fade and stub screens. Links live INSIDE
 * the screens: navigation goes through the router as in the app (`MemoryRouter` does not see
 * `window.history`, so poking it directly is pointless).
 */
function renderZone(initialPath: string) {
  return renderWithProviders(
    <Routes>
      <Route element={<PublicCrossfade />}>
        <Route
          path="/login"
          element={
            <div>
              screen-login
              <Link to="/signup">to-signup</Link>
            </div>
          }
        />
        <Route path="/signup" element={<div>screen-signup</div>} />
      </Route>
    </Routes>,
    { route: initialPath },
  );
}

/** The leaving screen has its own class, which is how it is recognized. */
function leavingScreen(): HTMLElement | null {
  return document.querySelector(".public-crossfade__screen--leaving");
}

describe("PublicCrossfade", () => {
  it("на старте показывает только текущий экран, уходящего нет", () => {
    renderZone("/login");

    expect(screen.getByText("screen-login")).toBeInTheDocument();
    expect(leavingScreen()).toBeNull();
  });

  it("при навигации держит оба экрана в DOM: входящий и уходящий", async () => {
    const { user } = renderZone("/login");

    await user.click(screen.getByText("to-signup"));

    // The point of the component: the old screen is NOT removed in the same frame but lives out the fade.
    expect(await screen.findByText("screen-signup")).toBeInTheDocument();
    await waitFor(() => expect(leavingScreen()).not.toBeNull());
    expect(screen.getByText("screen-login")).toBeInTheDocument();
  });

  it("уходящий экран помечен inert — фокус в него не проваливается", async () => {
    const { user } = renderZone("/login");

    await user.click(screen.getByText("to-signup"));

    await waitFor(() => expect(leavingScreen()).not.toBeNull());
    // Without inert a link inside the fading screen would stay in the Tab order.
    expect(leavingScreen()?.hasAttribute("inert")).toBe(true);
  });

  it("по истечении фейда уходящий экран снимается", async () => {
    const { user } = renderZone("/login");

    await user.click(screen.getByText("to-signup"));
    await waitFor(() => expect(leavingScreen()).not.toBeNull());

    // The timer lives in the component (delay + duration); wait for the real removal.
    await waitFor(() => expect(leavingScreen()).toBeNull(), { timeout: 3000 });
    expect(screen.queryByText("screen-login")).not.toBeInTheDocument();
  });
});

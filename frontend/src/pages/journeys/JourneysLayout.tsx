import { useMemo, useRef, type RefObject } from "react";
import { Outlet, useLocation } from "react-router";

import { AppHeader } from "../../components/AppHeader";
import { JourneysPanel } from "./JourneysPanel";
import { JourneysMapHost } from "./map/JourneysMapHost";
import { JourneysMapSceneProvider } from "./map/JourneysMapSceneProvider";
import { useBannerCloseGlide } from "./useBannerCloseGlide";
import "./journeys.css";

/** What the shell passes to sub-tabs via `<Outlet context>`. */
export interface JourneysOutletContext {
  /** Navigation panel: on desktop it lies over the left part of the map. */
  panelRef: RefObject<HTMLElement | null>;
}

/**
 * Journeys section shell: shared header and a permanent left sub-navigation panel. The content
 * of a sub-tab (map / lists / add) goes in via <Outlet/>, so the header and panel are not
 * remounted when switching. The world map is shared too: tabs publish what to draw on it
 * (`usePublishMapScene`) instead of rendering their own.
 *
 * On add-journey the shell gets the `journeys-shell--globe` modifier: there the globe is the
 * app-global `PersistentGlobeHost` UNDER the shell, which must be transparent (see journeys.css).
 * `data-globe-passthrough` lets events through to the globe; it only acts while the host is
 * interactive (contract in persistent-globe.css), so it is always set.
 */
export function JourneysLayout() {
  const { pathname } = useLocation();
  const shellClassName = pathname.startsWith("/journeys/add")
    ? "app-shell journeys-shell journeys-shell--globe"
    : "app-shell journeys-shell";
  const panelRef = useRef<HTMLElement>(null);
  const outletContext = useMemo<JourneysOutletContext>(() => ({ panelRef }), []);
  const stageRef = useRef<HTMLElement>(null);
  useBannerCloseGlide(stageRef);

  return (
    <div className={shellClassName} data-globe-passthrough>
      <AppHeader />

      <main ref={stageRef} className="journeys-stage">
        <JourneysMapSceneProvider>
          <JourneysPanel ref={panelRef} />
          <JourneysMapHost />
          <Outlet context={outletContext} />
        </JourneysMapSceneProvider>
      </main>
    </div>
  );
}

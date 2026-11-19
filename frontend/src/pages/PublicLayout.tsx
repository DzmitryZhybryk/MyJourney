import { PublicHeader } from "../components/PublicHeader";
import { PublicCrossfade } from "./PublicCrossfade";
import "./public-layout.css";

/**
 * Public zone shell: shared header + content via `<Outlet/>` (cross-faded).
 *
 * The globe background is NOT mounted here: it lives at the app root (`PersistentGlobeHost` in
 * `App`), shared by the public and authorized zones, and survives navigation between them
 * (login -> home included), so WebGL is not reloaded. This zone's content is transparent and sits
 * ABOVE the fixed globe (z-index in `public-layout.css`).
 *
 * Content goes through `PublicCrossfade`, not straight through `<Outlet/>`: it keeps the leaving
 * screen mounted during the fade and has its own `Suspense` so loading a neighbouring page's
 * chunk does not unmount the layout.
 */
export function PublicLayout() {
  return (
    <div className="public-layout">
      <PublicHeader />
      {/* `main` landmark: one wrapper for all three screens, so there are never two `main`
          elements in the document during a cross-fade. */}
      <main className="public-layout__content">
        <PublicCrossfade />
      </main>
    </div>
  );
}

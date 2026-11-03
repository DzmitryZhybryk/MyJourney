import { lazy, Suspense } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router";
import { Center, Loader } from "@mantine/core";

import { AuthProvider } from "./auth/AuthContext";
import { DocumentTitle } from "./components/DocumentTitle";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { GlobeSceneProvider } from "./components/globe/GlobeSceneProvider";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { PublicOnlyRoute } from "./components/PublicOnlyRoute";
import { CurrentUserProvider } from "./user/CurrentUserContext";

// Pages are lazy (one chunk per route), so the main bundle holds only the shell (router,
// providers, Mantine base). Heavy parts (3D globes, country borders for flat maps) go into the
// chunk of the page that needs them and are not loaded on, say, /login.
const HomePage = lazy(() => import("./pages/HomePage").then((m) => ({ default: m.HomePage })));
// Public zone: layout with the persistent globe background plus the landing. The globe is heavy,
// so PublicLayout is lazy too and loads only on public routes.
const PublicLayout = lazy(() =>
  import("./pages/PublicLayout").then((m) => ({ default: m.PublicLayout })),
);
const LandingPage = lazy(() =>
  import("./pages/LandingPage").then((m) => ({ default: m.LandingPage })),
);
const AddJourneyPage = lazy(() =>
  import("./pages/journeys/AddJourneyPage").then((m) => ({ default: m.AddJourneyPage })),
);
const JourneysLayout = lazy(() =>
  import("./pages/journeys/JourneysLayout").then((m) => ({ default: m.JourneysLayout })),
);
const JourneysMapView = lazy(() =>
  import("./pages/journeys/JourneysMapView").then((m) => ({ default: m.JourneysMapView })),
);
const MovementsMapView = lazy(() =>
  import("./pages/journeys/MovementsMapView").then((m) => ({ default: m.MovementsMapView })),
);
const AllJourneysView = lazy(() =>
  import("./pages/journeys/all/AllJourneysView").then((m) => ({ default: m.AllJourneysView })),
);
const LoginPage = lazy(() => import("./pages/LoginPage").then((m) => ({ default: m.LoginPage })));
const SignUpPage = lazy(() => import("./pages/SignUpPage").then((m) => ({ default: m.SignUpPage })));

// App-global globe background. Mounted once at the root (sibling of <Routes>) and survives ANY
// navigation, including login -> home: the WebGL instance is not reloaded, the camera just flies
// to a new face. Lazy so three.js and journeys data stay off the first-paint critical path
// (anonymous landing visitors do not use them); body (--app-bg) paints the first-frame night
// background.
const PersistentGlobeHost = lazy(() =>
  import("./components/globe/PersistentGlobeHost").then((m) => ({ default: m.PersistentGlobeHost })),
);

// Dark backdrop for when the host chunk fails to load: the app assumes a dark background, and
// without it content would sit on the plain body colour. The class lives in index.css (always
// loaded). A WebGL failure does NOT reach here: a boundary inside the host isolates it (see
// PersistentGlobeHost) so the CSS layer (framing + scrim) survives missing WebGL.
const globeFallback = <div className="persistent-globe__fallback" />;

// Full-screen centered loader while a route chunk loads.
function PageFallback() {
  return (
    <Center style={{ minHeight: "100vh" }}>
      <Loader />
    </Center>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <CurrentUserProvider>
          {/* Outside <Suspense>: the tab title must update immediately on a route change, without
              waiting for the page chunk. */}
          <DocumentTitle />
          <GlobeSceneProvider>
            {/*
             * The globe background is a SIBLING of <Routes>, outside its <Suspense>: it must not
             * unmount on a route change (WebGL would reload). Own ErrorBoundary in case the host
             * chunk fails to load; own Suspense(null) since body already paints the background.
             */}
            <ErrorBoundary fallback={globeFallback}>
              <Suspense fallback={null}>
                <PersistentGlobeHost />
              </Suspense>
            </ErrorBoundary>
            <Suspense fallback={<PageFallback />}>
              <Routes>
                {/*
                 * Public zone under a shared PublicLayout: the persistent globe background and
                 * header mount once and survive navigation inside it, so landing -> signup ->
                 * login does not reload WebGL; the camera just flies to another face.
                 */}
                <Route element={<PublicLayout />}>
                  <Route
                    path="/"
                    element={
                      <PublicOnlyRoute>
                        <LandingPage />
                      </PublicOnlyRoute>
                    }
                  />
                  <Route
                    path="/login"
                    element={
                      <PublicOnlyRoute>
                        <LoginPage />
                      </PublicOnlyRoute>
                    }
                  />
                  <Route
                    path="/signup"
                    element={
                      <PublicOnlyRoute>
                        <SignUpPage />
                      </PublicOnlyRoute>
                    }
                  />
                </Route>

                {/* Dashboard lives at /home ("/" is the public landing). */}
                <Route
                  path="/home"
                  element={
                    <ProtectedRoute>
                      <HomePage />
                    </ProtectedRoute>
                  }
                />
                {/*
                 * Journeys section: shared shell (header + panel) with sub-tabs via <Outlet/>.
                 * The index route is the map, "movements" the movements map, "all" the feed of all
                 * journeys ("all/<id>" its journey card: one route, so the feed stays mounted under
                 * the card), "add" the add-journey form; wishlist is a placeholder (element={null}).
                 */}
                <Route
                  path="/journeys"
                  element={
                    <ProtectedRoute>
                      <JourneysLayout />
                    </ProtectedRoute>
                  }
                >
                  <Route index element={<JourneysMapView />} />
                  <Route path="movements" element={<MovementsMapView />} />
                  <Route path="all/:journeyId?" element={<AllJourneysView />} />
                  <Route path="wishlist" element={null} />
                  <Route path="add" element={<AddJourneyPage />} />
                </Route>

                {/*
                 * Unknown path. Without it nothing matched and React Router rendered nothing: a
                 * blank screen with no header (nginx serves index.html for any URL). Redirect to
                 * the root: anonymous users land on the landing, logged-in ones go on to the
                 * dashboard. A real 404 page is a product decision (needs EN/RU copy).
                 */}
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </Suspense>
          </GlobeSceneProvider>
        </CurrentUserProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

import { StrictMode, Suspense } from "react";
import { createRoot } from "react-dom/client";
import { MantineProvider } from "@mantine/core";
import { QueryClientProvider } from "@tanstack/react-query";
import "./mantineStyles";
import App from "./App.tsx";
import { createQueryClient } from "./api/queryClient";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { installPinchZoomGuard } from "./components/pinchZoomGuard";
import { RootErrorFallback } from "./components/RootErrorFallback";
import { theme } from "./theme";
import "./i18n";
import "./index.css";

const queryClient = createQueryClient();
installPinchZoomGuard();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    {/*
      The dark scheme aligns Mantine with the product surface. With a light scheme its defaults
      (white checkbox box, grey disabled button, near-black error text) had to be overridden by
      hand on every dark surface.
    */}
    <MantineProvider theme={theme} defaultColorScheme="dark">
      <QueryClientProvider client={queryClient}>
        <ErrorBoundary fallback={<RootErrorFallback />}>
          <Suspense fallback={null}>
            <App />
          </Suspense>
        </ErrorBoundary>
      </QueryClientProvider>
    </MantineProvider>
  </StrictMode>
);

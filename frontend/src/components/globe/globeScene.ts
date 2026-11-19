import { createContext, useContext } from "react";

import type { GlobeRoute } from "./route";

/**
 * Rectangle reserved for the globe on a page (viewport coordinates of `getBoundingClientRect`).
 * The host frames and crops the sphere by it.
 */
export interface GlobeSlot {
  left: number;
  top: number;
  width: number;
  height: number;
}

/** What a page asks to show on its face of the globe. Read by the host. */
export interface GlobeSceneState {
  route: GlobeRoute | null;
  slot: GlobeSlot | null;
}

/**
 * Scene setters in a separate context with a stable reference: the publishing page does not
 * rerender on every slot measurement tick, and its tree (the form) lives its own life.
 */
export interface GlobeSceneActions {
  setRoute: (route: GlobeRoute | null) => void;
  setSlot: (slot: GlobeSlot | null) => void;
}

export const GlobeSceneContext = createContext<GlobeSceneState | null>(null);
export const GlobeSceneActionsContext = createContext<GlobeSceneActions | null>(null);

export function useGlobeScene(): GlobeSceneState {
  const ctx = useContext(GlobeSceneContext);
  if (ctx === null) {
    throw new Error("useGlobeScene must be used within a <GlobeSceneProvider>");
  }

  return ctx;
}

export function useGlobeSceneActions(): GlobeSceneActions {
  const ctx = useContext(GlobeSceneActionsContext);
  if (ctx === null) {
    throw new Error("useGlobeSceneActions must be used within a <GlobeSceneProvider>");
  }

  return ctx;
}

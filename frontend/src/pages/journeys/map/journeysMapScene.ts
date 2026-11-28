import { createContext, useContext, type ReactNode, type RefObject } from "react";

import type { MapCountry, WorldMapTone } from "../../../components/WorldMap";
import type { ViewBox } from "../../../components/worldProjection";

/** Journeys tabs that draw on the shared map. */
export type JourneysMapTab = "journeys" | "movements" | "feed";

/** What a tab asks the shared map to show. Field meanings match the `WorldMap` props. */
export interface JourneysMapScene {
  /** The tab that published the scene: a new tab resets manual zoom and flies to its frame. */
  tabId: JourneysMapTab;
  countries: readonly MapCountry[];
  tone: WorldMapTone;
  fitBounds?: ViewBox | null;
  occluderRef?: RefObject<HTMLElement | null>;
  shouldFadeUnderOccluder?: boolean;
  isFitAnimated?: boolean;
  isInteractive?: boolean;
  isLandMuted?: boolean;
  /** Background only: hidden from assistive technology. */
  isDecorative?: boolean;
  overlay?: (view: ViewBox) => ReactNode;
}

/**
 * Scene setter in a separate context with a stable reference: a publishing tab does not rerender
 * when the scene changes.
 */
export interface JourneysMapSceneActions {
  setScene: (scene: JourneysMapScene | null) => void;
}

export const JourneysMapSceneContext = createContext<JourneysMapScene | null | undefined>(undefined);
export const JourneysMapSceneActionsContext = createContext<JourneysMapSceneActions | null>(null);

export function useJourneysMapScene(): JourneysMapScene | null {
  const ctx = useContext(JourneysMapSceneContext);
  if (ctx === undefined) {
    throw new Error("useJourneysMapScene must be used within a <JourneysMapSceneProvider>");
  }

  return ctx;
}

export function useJourneysMapSceneActions(): JourneysMapSceneActions {
  const ctx = useContext(JourneysMapSceneActionsContext);
  if (ctx === null) {
    throw new Error("useJourneysMapSceneActions must be used within a <JourneysMapSceneProvider>");
  }

  return ctx;
}

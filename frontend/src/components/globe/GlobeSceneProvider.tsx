import { useMemo, useState, type ReactNode } from "react";

import {
  GlobeSceneActionsContext,
  GlobeSceneContext,
  type GlobeSceneActions,
  type GlobeSlot,
} from "./globeScene";
import type { GlobeRoute } from "./route";

interface GlobeSceneProviderProps {
  children: ReactNode;
}

/**
 * Channel from a page to the persistent globe. The host is a sibling of `<Routes>`, so the
 * provider sits above both. The module is light (no three, no textures) and is in the main chunk.
 */
export function GlobeSceneProvider({ children }: GlobeSceneProviderProps) {
  const [route, setRoute] = useState<GlobeRoute | null>(null);
  const [slot, setSlot] = useState<GlobeSlot | null>(null);

  const scene = useMemo(() => ({ route, slot }), [route, slot]);
  // useState setters are stable, so the object lives as long as the provider.
  const actions = useMemo<GlobeSceneActions>(() => ({ setRoute, setSlot }), []);

  return (
    <GlobeSceneActionsContext.Provider value={actions}>
      <GlobeSceneContext.Provider value={scene}>{children}</GlobeSceneContext.Provider>
    </GlobeSceneActionsContext.Provider>
  );
}

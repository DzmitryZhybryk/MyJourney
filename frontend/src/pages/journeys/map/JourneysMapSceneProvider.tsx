import { useMemo, useState, type ReactNode } from "react";

import {
  JourneysMapSceneActionsContext,
  JourneysMapSceneContext,
  type JourneysMapScene,
  type JourneysMapSceneActions,
} from "./journeysMapScene";

interface JourneysMapSceneProviderProps {
  children: ReactNode;
}

/** Channel from a Journeys tab to the shared map in the section shell. */
export function JourneysMapSceneProvider({ children }: JourneysMapSceneProviderProps) {
  const [scene, setScene] = useState<JourneysMapScene | null>(null);
  // The useState setter is stable, so the object lives as long as the provider.
  const actions = useMemo<JourneysMapSceneActions>(() => ({ setScene }), []);

  return (
    <JourneysMapSceneActionsContext.Provider value={actions}>
      <JourneysMapSceneContext.Provider value={scene}>{children}</JourneysMapSceneContext.Provider>
    </JourneysMapSceneActionsContext.Provider>
  );
}

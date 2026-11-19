import { useLayoutEffect } from "react";

import { useJourneysMapSceneActions, type JourneysMapScene } from "./journeysMapScene";

/**
 * Shows `scene` on the shared map; `null` means the tab has no map (the feed on a narrow screen).
 *
 * Published in a layout effect so the map updates before paint, in the same frame as the tab. The
 * scene is not cleared on unmount: the next tab overwrites it, so a switch never passes through an
 * empty map. The caller memoizes `scene`: a new object every render republishes it every render.
 */
export function usePublishMapScene(scene: JourneysMapScene | null): void {
  const { setScene } = useJourneysMapSceneActions();
  useLayoutEffect(() => {
    setScene(scene);
  }, [scene, setScene]);
}

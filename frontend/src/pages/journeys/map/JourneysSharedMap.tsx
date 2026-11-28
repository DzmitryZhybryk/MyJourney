import { WorldMap, type WorldMapLayer } from "../../../components/WorldMap";
import type { JourneysMapScene } from "./journeysMapScene";

interface JourneysSharedMapProps {
  scene: JourneysMapScene;
  /** The previous tab's layer, fading out during the flight. */
  leaving: WorldMapLayer | null;
  /** A new key drops the user's zoom and moves to the scene's frame (see `WorldMap`). */
  sceneKey: string;
  /** `false`: a new key lands on the frame at once instead of flying there. */
  isSceneChangeAnimated: boolean;
  /** `false` on screens without a map: the map fades out but stays mounted (see journeys.css). */
  isVisible: boolean;
}

/** The one world map of the Journeys section, drawn from the scene the current tab published. */
export function JourneysSharedMap({ scene, leaving, sceneKey, isSceneChangeAnimated, isVisible }: JourneysSharedMapProps) {
  const className = [
    "journeys-map",
    scene.isDecorative ? "journeys-map--background" : null,
    isVisible ? null : "journeys-map--hidden",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <WorldMap
      className={className}
      countries={scene.countries}
      tone={scene.tone}
      fitBounds={scene.fitBounds}
      occluderRef={scene.occluderRef}
      shouldFadeUnderOccluder={scene.shouldFadeUnderOccluder}
      isFitAnimated={scene.isFitAnimated}
      isInteractive={isVisible && scene.isInteractive !== false}
      isLandMuted={scene.isLandMuted}
      isDecorative={!isVisible || scene.isDecorative}
      overlay={scene.overlay}
      sceneKey={sceneKey}
      isSceneChangeAnimated={isSceneChangeAnimated}
      leaving={leaving}
    />
  );
}

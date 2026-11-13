/** The feed tab; the journey card lives under it, so the feed stays mounted behind the card. */
export const ALL_JOURNEYS_PATH = "/journeys/all";

/** Address of a journey's card: the route `all/:journeyId?` in App.tsx. */
export function journeyCardPath(journeyId: string): string {
  return `${ALL_JOURNEYS_PATH}/${journeyId}`;
}

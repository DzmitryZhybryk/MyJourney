const DEG = Math.PI / 180;

/**
 * Angular distance (central angle, radians) between two geo points, via haversine.
 *
 * Used by the trip route scene (`routeCameraPov`, `useRouteScene`): radians feed straight into the
 * camera altitude zoom and the arc height.
 */
export function centralAngleRad(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const phi1 = lat1 * DEG;
  const phi2 = lat2 * DEG;
  const dPhi = (lat2 - lat1) * DEG;
  const dLam = (lng2 - lng1) * DEG;
  const a = Math.sin(dPhi / 2) ** 2 + Math.cos(phi1) * Math.cos(phi2) * Math.sin(dLam / 2) ** 2;
  return 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

import type { GlobePov } from "./GlobeCanvas";

/*
 * Camera fly-in when the globe appears: the camera starts farther away and at the equator,
 * approaches and rotates at the same time. The rotation is part of the same motion: its speed
 * eases down exactly to the auto-rotation speed, so at the end the spin hands over to
 * OrbitControls seamlessly. The stock globe.gl flight (`pointOfView` with a duration) cannot do
 * this: its tween overwrites the camera position every frame and swallows auto-rotation.
 */

/** How many times farther the camera starts (the old form globe: 2.5 -> 1.7 is about 1.45). */
const REVEAL_DISTANCE_FACTOR = 1.45;
/** Degrees of longitude the globe spins during the fly-in on top of auto-rotation. */
const REVEAL_SPIN_DEG = 30;

/** Cubic ease-out: the derivative is zero at the end, so the speed hands over smoothly. */
function easeOutCubic(progress: number): number {
  return 1 - (1 - progress) ** 3;
}

/**
 * Point of view at a given fly-in step. `progress` is 0..1 (clamped); `spinDegPerSec` is the
 * signed auto-rotation speed in longitude at the end of the fly-in (0 for none). At
 * `progress = 1` the result is exactly `target`.
 */
export function revealPov(target: GlobePov, progress: number, spinDegPerSec: number, durationMs: number): GlobePov {
  const t = Math.min(Math.max(progress, 0), 1);
  const eased = easeOutCubic(t);
  const startAltitude = target.altitude * REVEAL_DISTANCE_FACTOR;
  const remainingSeconds = ((1 - t) * durationMs) / 1000;
  // The extra spin goes in the auto-rotation direction (or, without it, the way it would go).
  const spinDirection = spinDegPerSec > 0 ? 1 : -1;

  return {
    lat: target.lat * eased,
    lng: target.lng - spinDegPerSec * remainingSeconds - spinDirection * REVEAL_SPIN_DEG * (1 - t) ** 3,
    altitude: startAltitude + (target.altitude - startAltitude) * eased,
  };
}

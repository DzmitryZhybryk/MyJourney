/** The user asked for reduced motion: animations are replaced by an instant change. */
export function prefersReducedMotion(): boolean {
  return typeof window !== "undefined" && (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false);
}

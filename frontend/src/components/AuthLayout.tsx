import type { ReactNode } from "react";

import "./auth-layout.css";

interface AuthLayoutProps {
  /** Side the form appears on. Paired with the sphere framing (see below). */
  side: "left" | "right";
  children: ReactNode;
}

/**
 * Auth screen shell: a thin form positioner over the persistent globe from `PublicLayout`. It has
 * no globe or header of its own (both are mounted higher up and survive navigation), so landing ->
 * form reads as a camera fly-over, not a page load.
 *
 * `side` is explicit, not derived from the route: it is paired with the sphere framing in
 * `persistent-globe.css` (`data-screen` moves the globe to the OPPOSITE edge), and one half must
 * not change without the other. An explicit prop keeps that visible.
 */
export function AuthLayout({ side, children }: AuthLayoutProps) {
  return (
    <div className="auth-layout" data-side={side}>
      <div className="auth-layout__inner">{children}</div>
    </div>
  );
}

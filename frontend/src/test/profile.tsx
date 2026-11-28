import { ProfilePage } from "../pages/profile/ProfilePage";
import { makeVerifiedAuthValue, renderWithProviders } from "./render";

/** Mounts ProfilePage at /profile for a verified user; a test passes its own auth value or query client. */
export function renderProfile(options: Parameters<typeof renderWithProviders>[1] = {}) {
  return renderWithProviders(<ProfilePage />, { route: "/profile", authValue: makeVerifiedAuthValue(), ...options });
}

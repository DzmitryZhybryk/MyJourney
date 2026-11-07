import "./avatar-silhouette.css";

interface AvatarSilhouetteProps {
  /** Diameter in px. */
  size: number;
}

/**
 * Placeholder avatar until the user uploads a photo: a head-and-shoulders silhouette in theme
 * colours. Decorative: the surrounding control carries the accessible name.
 */
export function AvatarSilhouette({ size }: AvatarSilhouetteProps) {
  return (
    <svg
      className="avatar-silhouette"
      width={size}
      height={size}
      viewBox="0 0 64 64"
      aria-hidden="true"
      focusable="false"
    >
      <circle className="avatar-silhouette__disc" cx="32" cy="32" r="32" />
      <circle className="avatar-silhouette__figure" cx="32" cy="25" r="11" />
      <path className="avatar-silhouette__figure" d="M10 64c0-13 10-22 22-22s22 9 22 22z" />
    </svg>
  );
}

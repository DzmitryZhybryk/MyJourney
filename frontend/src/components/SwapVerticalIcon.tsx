/**
 * Inline "swap" icon: vertical up/down arrows. SVG, not Noto emoji, since it is a UI control:
 * drawn as a stroke in `currentColor` so it themes with the button.
 */
export function SwapVerticalIcon() {
  return (
    <svg
      width={20}
      height={20}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M7 4v15" />
      <path d="M4 7l3 -3l3 3" />
      <path d="M17 20v-15" />
      <path d="M14 17l3 3l3 -3" />
    </svg>
  );
}

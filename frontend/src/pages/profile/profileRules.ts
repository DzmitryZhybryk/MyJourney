// `String(50)` of `users.display_name`; counted in UTF-16 units, like the generated zod validator.
export const DISPLAY_NAME_MAX = 50;

/** Mantine validator for the display name: an i18n token, or `null` when the trimmed name fits. */
export function validateDisplayName(value: string): string | null {
  const trimmed = value.trim();
  if (trimmed.length === 0) return "profile:validation.nameRequired";
  if (trimmed.length > DISPLAY_NAME_MAX) return "profile:validation.nameMax";
  return null;
}

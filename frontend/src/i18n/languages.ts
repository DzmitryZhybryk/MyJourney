/**
 * Registry of supported languages: the ONLY place to touch when adding a language.
 *
 * To add one:
 *   1. add `{ code, nativeName }` to `SUPPORTED_LANGUAGES`;
 *   2. create `src/locales/<code>/` with the same namespace files as the other languages.
 *
 * `LanguageCode` is derived from the array (`as const`) and widens by itself.
 */

export interface LanguageMeta {
  readonly code: string;
  readonly nativeName: string;
}

export const SUPPORTED_LANGUAGES = [
  { code: "en", nativeName: "English" },
  { code: "ru", nativeName: "Русский" },
] as const satisfies readonly LanguageMeta[];

/** Union of supported language codes, derived from the registry. */
export type LanguageCode = (typeof SUPPORTED_LANGUAGES)[number]["code"];

/** Fallback when detection yields no supported language. */
export const DEFAULT_LANGUAGE: LanguageCode = "en";

/** Flat list of codes, for `supportedLngs` and the switcher. */
export const SUPPORTED_LANGUAGE_CODES: readonly LanguageCode[] = SUPPORTED_LANGUAGES.map(
  (language) => language.code,
);

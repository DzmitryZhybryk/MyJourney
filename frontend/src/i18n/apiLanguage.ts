import type { LanguageEnum } from "../api/sdk";

/**
 * Language to request city names in from the backend, given the UI language.
 *
 * i18n may hold a regional variant (`ru-RU`) while the backend knows only `en` and `ru`;
 * anything that is not Russian gets English names.
 */
export function toApiLanguage(language: string): LanguageEnum {
  return language.startsWith("ru") ? "ru" : "en";
}

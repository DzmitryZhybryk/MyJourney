/**
 * i18next setup.
 *
 * Locales load lazily (dynamic `import()`), so only the active language is in the bundle.
 * `LanguageDetector` picks the language: localStorage, then the browser language, then
 * `DEFAULT_LANGUAGE`.
 */

import i18n from "i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import resourcesToBackend from "i18next-resources-to-backend";
import { initReactI18next } from "react-i18next";

import { DEFAULT_LANGUAGE, SUPPORTED_LANGUAGE_CODES } from "./languages";

/** Translation namespaces. A locale file name is the namespace (`<code>/<ns>.json`). */
export const I18N_NAMESPACES = ["common", "auth", "errors", "journeys", "landing"] as const;

/** localStorage key holding the chosen language. */
export const LANGUAGE_STORAGE_KEY = "myjourney.language";

void i18n
  .use(LanguageDetector)
  .use(
    resourcesToBackend(
      (language: string, namespace: string) => import(`../locales/${language}/${namespace}.json`),
    ),
  )
  .use(initReactI18next)
  .init({
    fallbackLng: DEFAULT_LANGUAGE,
    supportedLngs: [...SUPPORTED_LANGUAGE_CODES],
    // ru-RU / en-US are normalized to the base language (ru / en)
    load: "languageOnly",
    nonExplicitSupportedLngs: true,
    ns: [...I18N_NAMESPACES],
    defaultNS: "common",
    // React already escapes values
    interpolation: { escapeValue: false },
    detection: {
      order: ["localStorage", "navigator"],
      lookupLocalStorage: LANGUAGE_STORAGE_KEY,
      caches: ["localStorage"],
    },
  });

// Keep <html lang> in sync with the active language (a11y / SEO)
i18n.on("languageChanged", (language) => {
  document.documentElement.lang = language;
});

export { i18n };

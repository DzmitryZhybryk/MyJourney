import { Button, Menu } from "@mantine/core";
import { useTranslation } from "react-i18next";

import { SUPPORTED_LANGUAGES } from "../i18n";

interface LanguageSwitcherProps {
  /**
   * Extra class on the button, to style the switcher for a dark background (e.g. on the landing
   * by overriding Mantine `--button-*` variables): the default `subtle`/`gray` assumes a light
   * header and is unreadable on dark.
   */
  className?: string;
}

/**
 * Language switcher. Options come from `SUPPORTED_LANGUAGES`, so a language added to the
 * registry appears here without touching the component. The i18next detector persists the choice
 * in localStorage.
 */
export function LanguageSwitcher({ className }: LanguageSwitcherProps = {}) {
  const { i18n, t } = useTranslation("common");
  const currentCode = i18n.resolvedLanguage ?? SUPPORTED_LANGUAGES[0].code;
  const current =
    SUPPORTED_LANGUAGES.find((language) => language.code === currentCode) ?? SUPPORTED_LANGUAGES[0];

  const handleSelect = (code: string) => {
    if (code !== currentCode) {
      void i18n.changeLanguage(code);
    }
  };

  return (
    <Menu position="bottom-end" withArrow shadow="md" radius="md" width={160}>
      <Menu.Target>
        <Button
          variant="subtle"
          color="gray"
          size="sm"
          radius="md"
          className={className}
          aria-label={t("language.label")}
        >
          {current.code.toUpperCase()}
        </Button>
      </Menu.Target>
      <Menu.Dropdown>
        <Menu.Label>{t("language.label")}</Menu.Label>
        {SUPPORTED_LANGUAGES.map((language) => (
          <Menu.Item
            key={language.code}
            onClick={() => handleSelect(language.code)}
            fw={language.code === current.code ? 700 : 400}
          >
            {language.nativeName}
          </Menu.Item>
        ))}
      </Menu.Dropdown>
    </Menu>
  );
}

import { ActionIcon, Button, Group, Text } from "@mantine/core";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { dismissVerifyBanner, isVerifyBannerDismissed } from "../auth/verifyBannerStorage";
import { GLIDE_MS } from "./glide";

// Body class for the glide's duration after the banner goes away: the globe on the journey form
// glides with the page layer instead of snapping (see persistent-globe.css).
const CLOSING_CLASS = "verify-banner-closing";
let closingTimer: number | undefined;

interface EmailVerificationBannerProps {
  onVerifyClick: () => void;
}

export function EmailVerificationBanner({ onVerifyClick }: EmailVerificationBannerProps) {
  const { t } = useTranslation("auth");
  const [dismissed, setDismissed] = useState<boolean>(() => isVerifyBannerDismissed());

  useEffect(() => {
    if (dismissed) {
      return;
    }

    // Mark body while the banner is visible. On /home this class lowers and shrinks the globe
    // background to free space for the banner (see persistent-globe.css); removing it on
    // close/unmount restores the full height. Harmless on other screens.
    document.body.classList.add("has-verify-banner");
    return () => {
      // Both classes change in the same style recalculation, so the transition the closing class
      // turns on also covers the scale the removed `has-verify-banner` changes.
      document.body.classList.remove("has-verify-banner");
      document.body.classList.add(CLOSING_CLASS);
      window.clearTimeout(closingTimer);
      closingTimer = window.setTimeout(() => document.body.classList.remove(CLOSING_CLASS), GLIDE_MS);
    };
  }, [dismissed]);

  if (dismissed) {
    return null;
  }

  const handleDismiss = () => {
    dismissVerifyBanner();
    setDismissed(true);
  };

  return (
    <section
      aria-label={t("verificationBanner.regionLabel")}
      style={{
        position: "relative",
        // On /home `.home-main` is out of flow (position:absolute) and would sit OVER the banner,
        // stealing clicks on Verify/x; z-index lifts the banner above it. On Journeys the banner
        // is in flow and z-index has no effect.
        zIndex: 2,
        width: "100%",
        // Informational strip on the night surface: sunset-tinted, not a light fill (a cream fill
        // read as a bright slab across the screen and fought the message).
        backgroundColor: "rgba(232, 147, 92, 0.12)",
        borderBottom: "1px solid rgba(232, 147, 92, 0.28)",
        // 48px right padding reserves a gutter for the x so the centered cluster does not overlap it.
        padding: "10px 48px",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      {/* Message + Verify now, centered. wrap: on narrow screens the button drops under the text
          instead of being clipped; flexShrink:0 keeps the button label from shrinking. */}
      <Group gap="sm" align="center" justify="center" wrap="wrap" style={{ rowGap: 8 }}>
        <Text size="sm" ta="center" style={{ color: "var(--text)" }}>
          {t("verificationBanner.message")}
        </Text>
        <Button
          size="xs"
          variant="filled"
          onClick={onVerifyClick}
          // Theme accent (primary) with a dark label: Mantine sets the label via an inline
          // variable, so set the final property, like the auth submit button.
          style={{ flexShrink: 0, color: "var(--on-accent)" }}
        >
          {t("verificationBanner.action")}
        </Button>
      </Group>
      {/* x dismiss in the right gutter (reserved padding, does not overlap the cluster). */}
      <ActionIcon
        variant="subtle"
        color="gray"
        // 44px is the minimum tap target (web/performance.md); fits the 48px gutter (right:2).
        size={44}
        aria-label={t("verificationBanner.dismissLabel")}
        onClick={handleDismiss}
        style={{
          position: "absolute",
          right: 2,
          top: "50%",
          transform: "translateY(-50%)",
          fontSize: 22,
          color: "var(--text-muted)",
        }}
      >
        ×
      </ActionIcon>
    </section>
  );
}

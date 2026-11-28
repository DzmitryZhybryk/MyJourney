import { Switch, Text } from "@mantine/core";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError, errorCodeToken, resolveErrorToken } from "../../api/errors";
import { useProfileUpdate } from "./useProfileUpdate";

interface ProfileConsentProps {
  isSubscribed: boolean;
}

/**
 * Marketing email consent, saved on toggle. While the request is in flight the switch shows the
 * requested position and is locked; a failure leaves the cached (saved) position.
 */
export function ProfileConsent({ isSubscribed }: ProfileConsentProps) {
  const { t } = useTranslation("profile");
  const update = useProfileUpdate();
  const [errorToken, setErrorToken] = useState<string | null>(null);

  const pendingValue = update.isPending ? update.variables.body?.marketingEmailsConsent : undefined;

  const handleChange = async (checked: boolean) => {
    setErrorToken(null);
    try {
      await update.mutateAsync({ body: { marketingEmailsConsent: checked } });
    } catch (error) {
      setErrorToken(errorCodeToken(error instanceof ApiError ? error.code : "network"));
    }
  };

  return (
    <div className="profile-consent">
      <Switch
        checked={pendingValue ?? isSubscribed}
        onChange={(event) => void handleChange(event.currentTarget.checked)}
        disabled={update.isPending}
        label={t("consent.label")}
        description={t("consent.description")}
        labelPosition="left"
        size="md"
        classNames={{
          root: "profile-consent__switch",
          body: "profile-consent__body",
          label: "profile-consent__label",
          description: "profile-consent__description",
        }}
      />
      {errorToken !== null && (
        <Text size="sm" fw={500} c="var(--text-error)" role="alert" mt="xs">
          {resolveErrorToken(errorToken)}
        </Text>
      )}
    </div>
  );
}

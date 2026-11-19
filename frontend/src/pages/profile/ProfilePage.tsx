import { Button, Loader, Text } from "@mantine/core";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { getCurrentAccountOptions, type CurrentUserResponse } from "../../api/sdk";
import { useAuth } from "../../auth/useAuth";
import { AppHeader } from "../../components/AppHeader";
import { AvatarSilhouette } from "../../components/AvatarSilhouette";
import { SoonBadge } from "../../components/SoonBadge";
import { useCurrentUser } from "../../user/useCurrentUser";
import { ProfileConsent } from "./ProfileConsent";
import { ProfileName } from "./ProfileName";
import "./profile.css";

const AVATAR_SIZE = 88;
// Holds the line height of a value until the account loads, so the rows do not jump.
const EMPTY_VALUE = " ";

/**
 * Profile: how the user is shown (avatar, display name), what they sign in with (username and
 * email, read-only) and what they receive (marketing emails).
 */
export function ProfilePage() {
  const { t } = useTranslation("profile");
  const currentUser = useCurrentUser();

  return (
    <div className="app-shell">
      <AppHeader />

      <main className="profile-main">
        <section className="profile-card" aria-label={t("title")}>
          {currentUser.status === "ready" && <ProfileContent user={currentUser.user} />}
          {currentUser.status === "error" && (
            <Text size="sm" fw={500} c="var(--text-error)" role="alert">
              {t("loadError")}
            </Text>
          )}
          {(currentUser.status === "loading" || currentUser.status === "anonymous") && (
            <Loader className="profile-card__loader" />
          )}
        </section>
      </main>
    </div>
  );
}

interface ProfileContentProps {
  user: CurrentUserResponse;
}

/**
 * The email-verified flag comes from the session, which the verification dialog refreshes, never
 * from the account response: that query is not invalidated after verification.
 */
function ProfileContent({ user }: ProfileContentProps) {
  const { t } = useTranslation("profile");
  const { isAuthenticated, emailVerified, openVerifyDialog } = useAuth();
  const account = useQuery({ ...getCurrentAccountOptions(), enabled: isAuthenticated });

  return (
    <>
      <div className="profile-identity">
        <AvatarSilhouette size={AVATAR_SIZE} />
        <div className="profile-identity__text">
          <ProfileName displayName={user.displayName} />
          <span className="profile-photo" aria-disabled="true">
            {t("photo.upload")}
            <SoonBadge />
          </span>
        </div>
      </div>

      <div className="profile-section">
        <dl className="profile-facts">
          <div className="profile-fact">
            <dt className="profile-fact__term">{t("account.username")}</dt>
            <dd className="profile-fact__value">{account.data?.username ?? EMPTY_VALUE}</dd>
          </div>
          <div className="profile-fact">
            <dt className="profile-fact__term">{t("account.email")}</dt>
            <dd className="profile-fact__value">
              <span className="profile-fact__email">{account.data?.email ?? EMPTY_VALUE}</span>
              {!emailVerified && (
                <span className="profile-unverified">
                  <span className="profile-unverified__mark">{t("account.unverified")}</span>
                  <Button size="compact-sm" variant="light" onClick={openVerifyDialog}>
                    {t("account.verify")}
                  </Button>
                </span>
              )}
            </dd>
          </div>
        </dl>
        {account.isError && (
          <Text size="sm" fw={500} c="var(--text-error)" role="alert" mt="xs">
            {t("account.loadError")}
          </Text>
        )}
      </div>

      <div className="profile-section">
        <ProfileConsent isSubscribed={user.marketingEmailsConsent} />
      </div>
    </>
  );
}

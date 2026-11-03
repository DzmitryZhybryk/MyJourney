import { Avatar, Burger, Drawer, Group, Indicator, Menu, Stack, UnstyledButton } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { useTranslation } from "react-i18next";
import { Link, useLocation, useNavigate } from "react-router";

import { logout } from "../api/sdk";
import { useAuth } from "../auth/useAuth";
import { useCurrentUser } from "../user/useCurrentUser";
import { BrandMark } from "./BrandMark";
import { EmailVerificationBanner } from "./EmailVerificationBanner";
import { LanguageSwitcher } from "./LanguageSwitcher";
import { SoonBadge } from "./SoonBadge";
import "./app-header.css";

// `soon: true` marks an unimplemented section: the tab renders inactive (not a link) with a
// "Soon" badge, visible as an announcement but leading nowhere.
const TABS = [
  { key: "journeys", to: "/journeys", soon: false },
  { key: "mind", to: "/mind", soon: true },
] as const;

/**
 * App header shared by all inner screens (Home, Journeys, ...): brand, primary navigation with
 * the active section highlighted, language picker and profile menu (logout is idempotent on the
 * backend). Renders the email verification banner under itself, the single place for it.
 *
 * On narrow screens (<sm) primary navigation moves into a burger Drawer; language and profile
 * stay in the header.
 */
export function AppHeader() {
  const { t } = useTranslation("common");
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const { emailVerified, clearSession, openVerifyDialog } = useAuth();
  const currentUser = useCurrentUser();
  const [drawerOpened, { open: openDrawer, close: closeDrawer }] = useDisclosure(false);

  // Until the profile loads, name is undefined and Mantine Avatar shows a generic icon.
  const profileName = currentUser.status === "ready" ? currentUser.user.displayName : undefined;

  const handleLogout = async () => {
    try {
      await logout({ throwOnError: true });
    } catch {
      // Logout is idempotent on the backend (204 even without a cookie); a network error must
      // not leave the user logged in locally.
    } finally {
      clearSession();
      navigate("/login");
    }
  };

  const isTabActive = (to: string) => pathname === to || pathname.startsWith(`${to}/`);

  return (
    <>
      <header className="app-header">
        <div className="app-header__brand">
          <BrandMark to="/home" />
        </div>

        <nav className="app-tabs" aria-label={t("nav.ariaPrimary")}>
          {TABS.map((tab) =>
            tab.soon ? (
              <span
                key={tab.key}
                className="app-tab app-tab--soon"
                aria-disabled="true"
                title={t("badge.comingSoon")}
              >
                {t(`nav.${tab.key}`)}
                <SoonBadge />
              </span>
            ) : (
              <Link
                key={tab.key}
                to={tab.to}
                className={isTabActive(tab.to) ? "app-tab app-tab--active" : "app-tab"}
                aria-current={isTabActive(tab.to) ? "page" : undefined}
              >
                {t(`nav.${tab.key}`)}
              </Link>
            ),
          )}
        </nav>

        <div className="app-header__user">
          <Group gap="xs" align="center" wrap="nowrap">
            <LanguageSwitcher />
            <Menu position="bottom-end" withArrow shadow="md" radius="md" width={200}>
              <Menu.Target>
                <UnstyledButton aria-label={t("profile.menuButton")} className="app-avatar-button">
                  <Indicator
                    disabled={emailVerified}
                    color="yellow"
                    size={10}
                    offset={4}
                    withBorder
                  >
                    <Avatar radius="xl" size="md" color="slate" name={profileName} />
                  </Indicator>
                </UnstyledButton>
              </Menu.Target>
              <Menu.Dropdown>
                <Menu.Label>{t("profile.account")}</Menu.Label>
                <Menu.Item>{t("profile.profile")}</Menu.Item>
                {!emailVerified && (
                  <Menu.Item onClick={openVerifyDialog}>{t("profile.verifyEmail")}</Menu.Item>
                )}
                <Menu.Divider />
                <Menu.Item color="red" onClick={handleLogout}>
                  {t("profile.logout")}
                </Menu.Item>
              </Menu.Dropdown>
            </Menu>

            <Burger
              opened={drawerOpened}
              onClick={openDrawer}
              hiddenFrom="md"
              size="sm"
              aria-label={t("nav.ariaPrimary")}
            />
          </Group>
        </div>
      </header>

      <Drawer opened={drawerOpened} onClose={closeDrawer} position="right" size="78%" padding="lg">
        <Stack gap="xs">
          {TABS.map((tab) =>
            tab.soon ? (
              <span
                key={tab.key}
                className="app-drawer-link app-drawer-link--soon"
                aria-disabled="true"
              >
                {t(`nav.${tab.key}`)}
                <SoonBadge />
              </span>
            ) : (
              <Link
                key={tab.key}
                to={tab.to}
                onClick={closeDrawer}
                className={
                  isTabActive(tab.to) ? "app-drawer-link app-drawer-link--active" : "app-drawer-link"
                }
                aria-current={isTabActive(tab.to) ? "page" : undefined}
              >
                {t(`nav.${tab.key}`)}
              </Link>
            ),
          )}
        </Stack>
      </Drawer>

      {!emailVerified && <EmailVerificationBanner onVerifyClick={openVerifyDialog} />}
    </>
  );
}

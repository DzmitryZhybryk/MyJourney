import { Button, Center, Stack, Text, Title } from "@mantine/core";
import { useTranslation } from "react-i18next";

/** Full-screen fallback of the root `ErrorBoundary`: avoids a blank screen on a render crash. */
export function RootErrorFallback() {
  const { t } = useTranslation(["common", "errors"]);

  return (
    <Center mih="100vh" p="md">
      <Stack align="center" gap="sm" maw={420}>
        {/* Semantic token, not a palette shade: the product surface is night and `slate.8`
            (#1e293b) gave ~1.3:1 contrast here, making the heading invisible. */}
        <Title order={2} size="h3" style={{ color: "var(--text)" }}>
          {t("error.title", { ns: "common" })}
        </Title>
        <Text c="var(--text-muted)" ta="center">
          {t("fallback", { ns: "errors" })}
        </Text>
        <Button variant="light" onClick={() => window.location.reload()}>
          {t("error.reload", { ns: "common" })}
        </Button>
      </Stack>
    </Center>
  );
}

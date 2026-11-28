import { Button, PasswordInput, Stack, TextInput } from "@mantine/core";
import { useForm } from "@mantine/form";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router";
import { AuthCard } from "../components/AuthCard";
import { authInputClassNames, authPasswordClassNames } from "../components/authInputClasses";
import { AuthLayout } from "../components/AuthLayout";
import { applyApiError, resolveErrorToken, withLocalizedError } from "../api/errors";
import { login } from "../api/sdk";
import { useAuth } from "../auth/useAuth";

type LoginFormValues = {
  login: string;
  password: string;
};

export function LoginPage() {
  const { t } = useTranslation("auth");
  const navigate = useNavigate();
  const { setAccessToken } = useAuth();
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // `controlled` (not `uncontrolled`) because rendering depends on field values: the submit
  // button is disabled until the form is filled (see `canSubmit` below).
  const form = useForm<LoginFormValues>({
    mode: "controlled",
    initialValues: {
      login: "",
      password: "",
    },
    // Validators return an i18n TOKEN (`auth:validation.*`), not text: it is resolved at render
    // (`withLocalizedError`) so the error follows a language switch.
    validate: {
      login: (value) => (value.trim().length === 0 ? "auth:validation.loginRequired" : null),
      password: (value) => (value.length === 0 ? "auth:validation.passwordRequired" : null),
    },
  });

  // The button waits for the form to be FILLED, not valid: rules (length, format) are checked on
  // submit and explain themselves with a message under the field. Disabling by validity would
  // leave the user facing a dead button with no idea what is wrong.
  const formValues = form.getValues();
  const canSubmit = formValues.login.trim().length > 0 && formValues.password.length > 0;

  const handleSubmit = async (values: LoginFormValues) => {
    setFormError(null);
    setSubmitting(true);
    try {
      const { accessToken } = await login({
        body: { login: values.login.trim(), password: values.password },
        throwOnError: true,
      });
      setAccessToken(accessToken);
      navigate("/home");
    } catch (err) {
      // An operation error (bad credentials, network) goes at form level by the submit button;
      // applyApiError attaches field-bound errors to the fields itself.
      const message = applyApiError(err, form);
      if (message) {
        setFormError(message);
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    // Form on the right: the sphere moves left on this screen (persistent-globe.css).
    <AuthLayout side="right">
      <AuthCard title={t("login.title")} subtitle={t("login.subtitle")}>
        <form onSubmit={form.onSubmit(handleSubmit)}>
          <Stack gap="md">
            <TextInput
              label={t("login.loginLabel")}
              placeholder={t("login.loginPlaceholder")}
              size="md"
              radius="md"
              autoComplete="username"
              name="username"
              classNames={authInputClassNames}
              {...withLocalizedError(form.getInputProps("login"))}
            />

            <PasswordInput
              label={t("login.passwordLabel")}
              placeholder={t("login.passwordPlaceholder")}
              size="md"
              radius="md"
              autoComplete="current-password"
              name="password"
              classNames={authPasswordClassNames}
              {...withLocalizedError(form.getInputProps("password"))}
            />

            {/*
              Password recovery is not implemented yet. A dead `href="#"` link would be tabbable and
              announced as a link while doing nothing; a `<span>` is not focusable and does not pretend
              to be interactive. The hint stays visible to keep the password field's context.
              Restore `<Anchor to="/reset-password">` once the flow exists.
            */}
            <span className="auth-card__hint" style={{ alignSelf: "flex-end" }}>
              {t("login.forgotPassword")}
            </span>

            {/* `role="alert"`, otherwise a failed login is visible only to sighted users: the node
                appears conditionally and the live region announces it when it appears. */}
            {formError && (
              <p className="auth-card__error" role="alert">
                {resolveErrorToken(formError)}
              </p>
            )}

            <Button
              type="submit"
              size="md"
              radius="md"
              fullWidth
              mt="xs"
              className="auth-submit"
              disabled={!canSubmit}
              loading={submitting}
            >
              {t("login.submit")}
            </Button>
          </Stack>
        </form>

        <p className="auth-card__switch">
          {t("login.headerHint")} <Link to="/signup">{t("login.headerAction")}</Link>
        </p>
      </AuthCard>
    </AuthLayout>
  );
}

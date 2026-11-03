import { Anchor, Button, Checkbox, PasswordInput, Stack, TextInput } from "@mantine/core";
import { useForm } from "@mantine/form";
import { useState } from "react";
import { Trans, useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router";
import { AuthCard } from "../components/AuthCard";
import {
  authCheckboxClassNames,
  authInputClassNames,
  authPasswordClassNames,
} from "../components/authInputClasses";
import { AuthLayout } from "../components/AuthLayout";
import { applyApiError, resolveErrorToken, withLocalizedError } from "../api/errors";
import { register } from "../api/sdk";
import { useAuth } from "../auth/useAuth";

type SignUpFormValues = {
  username: string;
  email: string;
  password: string;
  termsAccepted: boolean;
  marketingEmailsConsent: boolean;
};

export function SignUpPage() {
  const { t } = useTranslation("auth");
  const navigate = useNavigate();
  const { setAccessToken } = useAuth();
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // `controlled` (not `uncontrolled`) because rendering depends on field values: the submit
  // button is disabled until the form is filled (see `canSubmit` below).
  const form = useForm<SignUpFormValues>({
    mode: "controlled",
    initialValues: {
      username: "",
      email: "",
      password: "",
      termsAccepted: false,
      marketingEmailsConsent: false,
    },
    // Validators return an i18n TOKEN (`auth:validation.*`), not text: it is resolved at render
    // (`withLocalizedError`), so an error already on screen follows a language switch.
    validate: {
      username: (value) => {
        const trimmed = value.trim();
        if (trimmed.length < 3) return "auth:validation.usernameMin";
        if (trimmed.length > 50) return "auth:validation.usernameMax";
        return null;
      },
      email: (value) => {
        const trimmed = value.trim();
        if (!/^\S+@\S+\.\S+$/u.test(trimmed)) return "auth:validation.emailInvalid";
        if (trimmed.length > 254) return "auth:validation.emailTooLong";
        return null;
      },
      password: (value) => {
        if (value.length < 8) return "auth:validation.passwordMin";
        if (value.length > 50) return "auth:validation.passwordMax";
        return null;
      },
      termsAccepted: (value) => (value ? null : "auth:validation.termsRequired"),
    },
  });

  // The button waits for the form to be FILLED, not valid: rules (length, format) are checked on
  // submit and explain themselves with a message under the field. Disabling by validity would
  // leave the user facing a dead button with no idea what is wrong.
  // Accepting the terms is part of that minimum; the newsletter consent is optional.
  const formValues = form.getValues();
  const canSubmit =
    formValues.username.trim().length > 0 &&
    formValues.email.trim().length > 0 &&
    formValues.password.length > 0 &&
    formValues.termsAccepted;

  const handleSubmit = async (values: SignUpFormValues) => {
    setFormError(null);
    setSubmitting(true);
    try {
      const { accessToken } = await register({
        body: {
          username: values.username.trim(),
          email: values.email.trim(),
          password: values.password,
          termsAccepted: values.termsAccepted,
          marketingEmailsConsent: values.marketingEmailsConsent,
        },
        throwOnError: true,
      });
      setAccessToken(accessToken);
      navigate("/home");
    } catch (err) {
      setFormError(applyApiError(err, form));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    // Form on the left: the sphere moves right on this screen (persistent-globe.css).
    <AuthLayout side="left">
      <AuthCard title={t("signup.title")} subtitle={t("signup.subtitle")}>
        <form onSubmit={form.onSubmit(handleSubmit)}>
          <Stack gap="md">
            <TextInput
              label={t("signup.usernameLabel")}
              placeholder={t("signup.usernamePlaceholder")}
              size="md"
              radius="md"
              autoComplete="username"
              name="username"
              classNames={authInputClassNames}
              {...withLocalizedError(form.getInputProps("username"))}
            />

            <TextInput
              label={t("signup.emailLabel")}
              placeholder={t("signup.emailPlaceholder")}
              size="md"
              radius="md"
              autoComplete="email"
              name="email"
              classNames={authInputClassNames}
              {...withLocalizedError(form.getInputProps("email"))}
            />

            <PasswordInput
              label={t("signup.passwordLabel")}
              placeholder={t("signup.passwordPlaceholder")}
              size="md"
              radius="md"
              autoComplete="new-password"
              name="password"
              classNames={authPasswordClassNames}
              {...withLocalizedError(form.getInputProps("password"))}
            />

            <Checkbox
              size="sm"
              classNames={authCheckboxClassNames}
              {...withLocalizedError(form.getInputProps("termsAccepted", { type: "checkbox" }))}
              label={
                <Trans
                  t={t}
                  i18nKey="signup.terms"
                  components={{
                    tos: <Anchor href="/terms" target="_blank" rel="noopener noreferrer" />,
                    privacy: (
                      <Anchor href="/privacy" target="_blank" rel="noopener noreferrer" />
                    ),
                  }}
                />
              }
            />

            <Checkbox
              size="sm"
              classNames={authCheckboxClassNames}
              label={t("signup.marketing")}
              {...form.getInputProps("marketingEmailsConsent", { type: "checkbox" })}
            />

            {/* An operation error (409, network) goes by the button, not in the card header: the
                "UI error display" rule keeps an operation-scoped message next to the action that
                caused it. `role="alert"` announces the failure to screen readers; the node appears
                conditionally, so it fires exactly on an error. */}
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
              {t("signup.submit")}
            </Button>
          </Stack>
        </form>

        <p className="auth-card__switch">
          {t("signup.headerHint")} <Link to="/login">{t("signup.headerAction")}</Link>
        </p>
      </AuthCard>
    </AuthLayout>
  );
}

---
paths:
  - "frontend/src/**/*.tsx"
  - "frontend/src/locales/**"
---

# UI error display (forms and dialogs)

One visual language for **every** user-facing error in a form or dialog. A filled `<Alert>` is
reserved for persistent informational banners (the email-verification banner), never for transient
or validation errors.

## Style

- Plain red text, medium weight: `<Text size="sm" c="red" fw={500}>`, or Mantine's field error via
  `form.setFieldError` (weight is set globally in `index.css`). No background, no border, no icon.
  Emphasis comes from color and weight, not size.
- The input itself stays neutral: no red border, placeholder or icon. Only the message below it is
  red (enforced globally in `frontend/src/index.css`).

## Placement

- Field-scoped (tied to one input) → directly under that field via `form.setFieldError(field, msg)`;
  for non-form controls (e.g. `PinInput`) render the red `<Text>` right under the control.
- Operation-scoped (the whole action failed) → at form level, next to the primary action (under the
  submit button or by the dialog actions).

## Text and language switching

The text is owned by the frontend (i18n), never the backend `message` (it is Russian and will not
match the UI language).

**Resolve at render, store a token.** A resolved string kept in state or `form.errors` is frozen in
the language it was resolved in, so switching language leaves the old error behind. Store an i18n
token and resolve it during render, where `useTranslation` re-renders on a language change:

- Backend error code → `errorCodeToken(code)` (yields `errors:<code>`), resolved by
  `resolveErrorToken` / `messageForCode`. `applyApiError` already returns and sets tokens.
- Frontend validation → the Mantine validator returns the **namespaced i18n key**
  (`"auth:validation.usernameMin"`), not `t(...)`.
- At the render site: `resolveErrorToken(token)` for explicit `error=` props and error state, or
  `withLocalizedError(form.getInputProps(field))` for the `error` inside Mantine input props.

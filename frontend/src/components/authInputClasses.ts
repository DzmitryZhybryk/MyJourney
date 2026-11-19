/*
 * Styles API classes for auth form fields on the dark glass (styles are in `auth-card.css`).
 *
 * Style inputs via `classNames`, NOT selectors like `.mantine-Input-input`: Mantine 9 gives a
 * stable static name only to the wrapper (`mantine-Input-wrapper`); other nodes get hashed
 * classes. Our own class is the only version-proof hook on the input itself.
 */

export const authInputClassNames = { input: "auth-input", label: "auth-label" };

/** Same for PasswordInput: the real field is nested inside the "input" wrapper. */
export const authPasswordClassNames = {
  ...authInputClassNames,
  innerInput: "auth-input__inner",
  section: "auth-input__section",
};

/** Checkboxes: the box (`input` is the real `<input>`) and the tick (`icon`, its sibling). */
export const authCheckboxClassNames = {
  input: "auth-checkbox",
  icon: "auth-checkbox__icon",
  label: "auth-label--checkbox",
};

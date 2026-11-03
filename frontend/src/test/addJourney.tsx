import type { QueryClient } from "@tanstack/react-query";
import type { UserEvent } from "@testing-library/user-event";

import { AddJourneyPage } from "../pages/journeys/AddJourneyPage";
import { renderRoutes, screen, waitFor, within } from "./render";

/** Mounts AddJourneyPage at /journeys/add with a landing marker for the submit target path. */
export function renderAddJourney(queryClient?: QueryClient) {
  return renderRoutes({
    element: <AddJourneyPage />,
    path: "/journeys/add",
    landings: [{ path: "/journeys", label: "journeys-landing" }],
    queryClient,
  });
}

// hidden: true, because a Mantine Combobox/Select dropdown (Popover/Floating UI) gets no computed
// position in jsdom and stays display:none, so options are outside the visible a11y tree.

/**
 * Types a query into the autocomplete field and picks a candidate.
 *
 * The option lookup is scoped to THIS field's dropdown (via the input's `aria-controls`): Mantine
 * Combobox keeps a neighbouring field's closed dropdown in the DOM (`keepMounted`), and a
 * same-named option from there would otherwise hijack the pick (From and To with the same city).
 */
export async function pickCity(options: {
  user: UserEvent;
  label: string;
  query: string;
  option: RegExp;
}): Promise<void> {
  const { user, label, query, option } = options;
  const input = screen.getByLabelText(label);
  await user.type(input, query);
  const listbox = await waitFor(() => {
    const listboxId = input.getAttribute("aria-controls");
    const element = listboxId ? document.getElementById(listboxId) : null;
    if (!element) {
      throw new Error("дропдаун поля ещё не привязан");
    }
    return element;
  });
  await user.click(await within(listbox).findByRole("option", { name: option, hidden: true }));
}

/** Opens a Mantine Select by its trigger and clicks the option by exact name. */
export async function pickOption(options: { user: UserEvent; trigger: HTMLElement; option: string }): Promise<void> {
  const { user, trigger, option } = options;
  await user.click(trigger);
  await user.click(await screen.findByRole("option", { name: option, hidden: true }));
}

/** Fills the form Moscow -> London, plane, 2020, without submitting. */
export async function fillMoscowToLondon(user: UserEvent): Promise<void> {
  await pickCity({ user, label: "From", query: "Mos", option: /Moscow/iu });
  await pickCity({ user, label: "To", query: "Lon", option: /London/iu });
  await pickOption({ user, trigger: screen.getByPlaceholderText("Choose transport"), option: "Air" });
  await pickOption({ user, trigger: screen.getByPlaceholderText("Select year"), option: "2020" });
}

/** Fills the form Moscow -> London, plane, 2020 and submits it. */
export async function submitMoscowToLondon(user: UserEvent): Promise<void> {
  await fillMoscowToLondon(user);
  await user.click(screen.getByRole("button", { name: "Add journey" }));
}

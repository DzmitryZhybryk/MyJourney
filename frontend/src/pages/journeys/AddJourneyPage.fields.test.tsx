import { describe, expect, it } from "vitest";

import { renderAddJourney } from "../../test/addJourney";
import { screen, waitFor } from "../../test/render";

describe("AddJourneyPage — поля формы", () => {
  it("Enter по подсказке выбирает город и уводит фокус на поле второго города", async () => {
    const { user } = renderAddJourney();

    await user.type(screen.getByLabelText("From"), "Mos");
    await screen.findByRole("option", { name: /Moscow/iu, hidden: true });
    await user.keyboard("{Enter}");

    expect(screen.getByLabelText("From")).toHaveValue("Moscow");
    await waitFor(() => expect(screen.getByLabelText("To")).toHaveFocus());
  });

  it("Tab по открытой подсказке работает как Enter: выбор + фокус на втором городе (не на кнопке)", async () => {
    const { user } = renderAddJourney();

    await user.type(screen.getByLabelText("From"), "Mos");
    await screen.findByRole("option", { name: /Moscow/iu, hidden: true });
    await user.tab();

    expect(screen.getByLabelText("From")).toHaveValue("Moscow");
    await waitFor(() => expect(screen.getByLabelText("To")).toHaveFocus());
  });

  it("в выборе года есть текущий год, но нет следующего", async () => {
    const { user } = renderAddJourney();
    const currentYear = new Date().getFullYear();

    await user.click(screen.getByPlaceholderText("Select year"));

    expect(await screen.findByRole("option", { name: String(currentYear), hidden: true })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: String(currentYear + 1), hidden: true })).not.toBeInTheDocument();
  });
});

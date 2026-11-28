import { expect, test } from "../fixtures";

/**
 * E2E: profile page (flow P).
 *
 * Real stack: `PATCH /v1/users/me/` writes the change; a reload reads it back from the database, so
 * the checks prove persistence, not only the client cache.
 */
test.describe("Profile", () => {
  test("переименование видно на странице, в меню шапки и в приветствии после перезагрузки", async ({
    authedPage,
  }) => {
    const newName = `Traveler ${Date.now().toString(36)}`;
    await authedPage.goto("/profile");

    const nameValue = authedPage.getByRole("heading", { level: 1 }).getByRole("button");
    await nameValue.click();
    const input = authedPage.getByRole("textbox", { name: "Name" });
    await input.fill(`  ${newName}  `);
    await input.press("Enter");

    await expect(authedPage.getByRole("heading", { name: newName, level: 1 })).toBeVisible();

    await authedPage.reload();
    await expect(authedPage.getByRole("heading", { name: newName, level: 1 })).toBeVisible();
    await authedPage.getByRole("button", { name: "Open profile menu" }).click();
    await expect(authedPage.getByRole("menu").getByText(newName, { exact: true })).toBeVisible();

    await authedPage.goto("/home");
    await expect(authedPage.getByText(`Hello, ${newName}`)).toBeVisible();
  });

  test("согласие на рассылку переключается и сохраняется после перезагрузки", async ({ authedPage }) => {
    await authedPage.goto("/profile");
    const consent = authedPage.getByRole("switch", { name: /^Product updates and news by email/u });
    await expect(consent).not.toBeChecked();

    await consent.click({ force: true });
    await expect(consent).toBeChecked();
    await expect(consent).toBeEnabled();

    await authedPage.reload();
    await expect(authedPage.getByRole("switch", { name: /^Product updates and news by email/u })).toBeChecked();
  });
});

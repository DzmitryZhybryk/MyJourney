import { expect, test } from "@playwright/test";

import { E2E_ADMIN, HAS_E2E_ADMIN } from "../helpers/admin";
import { loginViaUi } from "../helpers/users";

/**
 * E2E: the admin changes an upload limit (flow M).
 *
 * One global config is shared by every browser project, so the flow runs once, in chromium, serially:
 * parallel saves would answer each other with 409. A reload proves the new version came from the server.
 */
test.describe.configure({ mode: "serial" });

test.describe("Admin: upload rules", () => {
  test.skip(!HAS_E2E_ADMIN, "only the throwaway stack (make test-e2e) has the e2e admin");

  test("админ меняет лимит аватара и видит новую версию после перезагрузки", async ({ page, browserName }) => {
    test.skip(browserName !== "chromium", "one shared config: the flow runs in one browser only");

    await loginViaUi(page, E2E_ADMIN);
    await page.getByRole("button", { name: "Open profile menu" }).click();
    await page.getByRole("menuitem", { name: "Admin" }).click();
    await expect(page.getByRole("heading", { name: "Upload rules", level: 1 })).toBeVisible();

    const versionBefore = Number(await page.getByText(/^\d+$/u).first().textContent());
    const avatar = page.getByRole("region", { name: "Avatar" });
    const sizeButton = avatar.getByRole("button", { name: /^Size up to:/u });
    const sizeBefore = Number(/\d+/u.exec((await sizeButton.textContent()) ?? "")?.[0]);
    const newSize = String(sizeBefore + 1);
    await sizeButton.click();
    const field = avatar.getByRole("textbox", { name: "Size up to" });
    await field.fill(newSize);
    await page.getByRole("button", { name: "Save" }).click();

    await expect(page.getByRole("button", { name: "Save" })).toBeHidden();
    await page.reload();
    await expect(avatar.getByRole("button", { name: `Size up to: ${newSize} MB` })).toBeVisible();
    await expect(page.getByText(String(versionBefore + 1), { exact: true })).toBeVisible();
  });
});

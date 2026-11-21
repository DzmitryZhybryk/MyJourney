import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import type { UpdateMediaConfigRequest } from "../../api/sdk";
import { server, TEST_MEDIA_CONFIG } from "../../test/handlers";
import { makeAuthValue, renderWithProviders, screen, waitFor, within } from "../../test/render";
import { MediaConfigPage } from "./MediaConfigPage";

const MEGABYTE = 1024 * 1024;

function renderPage() {
  return renderWithProviders(<MediaConfigPage />, {
    authValue: makeAuthValue({ isAuthenticated: true, emailVerified: true }),
  });
}

describe("MediaConfigPage", () => {
  it("показывает версию, автора деплоя и подпись стороны по оси из кода", async () => {
    renderPage();

    expect(await screen.findByText("Initial value")).toBeInTheDocument();
    expect(screen.getByText("Short side from")).toBeInTheDocument();
    expect(screen.getByText("Long side from")).toBeInTheDocument();
    expect(
      within(screen.getByRole("region", { name: "Avatar" })).getByRole("button", { name: "Size up to: 30 MB" }),
    ).toBeInTheDocument();
  });

  it("правка числа сразу даёт кнопку сохранения, а сохранение шлёт весь конфиг в байтах с версией", async () => {
    let sentBody: UpdateMediaConfigRequest | null = null;
    server.use(
      http.put("/v1/admin/media/config/", async ({ request }) => {
        sentBody = (await request.json()) as UpdateMediaConfigRequest;
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const { user } = renderPage();

    const avatar = await screen.findByRole("region", { name: "Avatar" });
    await user.click(within(avatar).getByRole("button", { name: "Size up to: 30 MB" }));
    const field = within(avatar).getByRole("textbox", { name: "Size up to" });
    await user.clear(field);
    await user.type(field, "20");
    await user.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => expect(sentBody).not.toBeNull());
    expect(sentBody).toEqual({
      editedVersion: 1,
      snapshot: {
        ...TEST_MEDIA_CONFIG.snapshot,
        avatar: { ...TEST_MEDIA_CONFIG.snapshot.avatar, maxSizeBytes: 20 * MEGABYTE },
      },
    });
  });

  it("снятый формат попадает в черновик, «Discard» возвращает сохранённый конфиг", async () => {
    const { user } = renderPage();

    const [avatarPng] = await screen.findAllByRole("checkbox", { name: "PNG" });
    await user.click(avatarPng);

    expect(screen.getByText("1 change not saved")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Discard" }));

    expect(screen.queryByRole("button", { name: "Save" })).toBeNull();
    expect(screen.getAllByRole("checkbox", { name: "PNG" })[0]).toBeChecked();
  });

  it("последний формат вида снять нельзя", async () => {
    const { user } = renderPage();

    const [videoMp4] = await screen.findAllByRole("checkbox", { name: "MP4" });
    await user.click(videoMp4);

    expect(videoMp4).toBeChecked();
    expect(screen.queryByRole("button", { name: "Save" })).toBeNull();
  });

  it("на 409 сообщает, что правила уже сохранили, и сбрасывает черновик", async () => {
    server.use(
      http.put("/v1/admin/media/config/", () =>
        HttpResponse.json({ code: "config_version_conflict", message: "x" }, { status: 409 }),
      ),
    );
    const { user } = renderPage();

    const [avatarPng] = await screen.findAllByRole("checkbox", { name: "PNG" });
    await user.click(avatarPng);
    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Someone saved these rules while you were editing");
  });
});

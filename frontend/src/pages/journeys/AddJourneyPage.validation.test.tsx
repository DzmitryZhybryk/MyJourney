import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { server } from "../../test/handlers";
import { pickCity, pickOption, renderAddJourney } from "../../test/addJourney";
import { screen } from "../../test/render";

describe("AddJourneyPage — проверка формы до отправки", () => {
  it("требует обязательные поля и не отправляет запрос при пустой форме", async () => {
    let posted = false;
    server.use(
      http.post("/v1/journeys/", () => {
        posted = true;
        return new HttpResponse(null, { status: 201 });
      }),
    );
    const { user } = renderAddJourney();

    await user.click(screen.getByRole("button", { name: "Add journey" }));

    expect(await screen.findByText("Choose the departure city")).toBeInTheDocument();
    expect(screen.getByText("Choose the destination city")).toBeInTheDocument();
    expect(screen.getByText("Choose a transport type")).toBeInTheDocument();
    expect(screen.getByText("Choose a year")).toBeInTheDocument();
    expect(posted).toBe(false);
  });

  it("блокирует одинаковые города отправления и назначения, не отправляя запрос", async () => {
    let posted = false;
    server.use(
      http.post("/v1/journeys/", () => {
        posted = true;
        return new HttpResponse(null, { status: 201 });
      }),
    );
    const { user } = renderAddJourney();

    await pickCity({ user, label: "From", query: "Mos", option: /Moscow/iu });
    await pickCity({ user, label: "To", query: "Mos", option: /Moscow/iu });
    await pickOption({ user, trigger: screen.getByPlaceholderText("Choose transport"), option: "Air" });
    await pickOption({ user, trigger: screen.getByPlaceholderText("Select year"), option: "2020" });

    await user.click(screen.getByRole("button", { name: "Add journey" }));

    expect(await screen.findByText("Departure and destination must differ")).toBeInTheDocument();
    expect(posted).toBe(false);
  });
});

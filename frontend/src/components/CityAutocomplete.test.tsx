import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { GEO_CITIES, server } from "../test/handlers";
import { renderWithProviders, screen, waitFor } from "../test/render";
import { CityAutocomplete } from "./CityAutocomplete";

// Margin over the component debounce (DEBOUNCE_MS = 250): how long to wait so a deferred request
// would have gone out if the "text equals the picked city" guard did not work.
const DEBOUNCE_SETTLE_MS = 400;

describe("CityAutocomplete", () => {
  it("ищет города по префиксу и кладёт выбранный город в onChange", async () => {
    const onChange = vi.fn();
    const { user } = renderWithProviders(
      <CityAutocomplete label="From" placeholder="City" value={null} onChange={onChange} />,
    );

    await user.type(screen.getByLabelText("From"), "Mos");
    // hidden: true, because a Mantine Combobox dropdown (Popover/Floating UI) gets no computed
    // position in jsdom and stays display:none, so the option is outside the visible a11y tree.
    await user.click(await screen.findByRole("option", { name: /Moscow/iu, hidden: true }));

    expect(onChange).toHaveBeenCalledWith(GEO_CITIES[0]);
  });

  it("название, набранное целиком руками (в любом регистре), засчитывается при уходе из поля", async () => {
    const onChange = vi.fn();
    const { user } = renderWithProviders(
      <CityAutocomplete label="From" placeholder="City" value={null} onChange={onChange} />,
    );

    await user.type(screen.getByLabelText("From"), "moscow");
    await screen.findByRole("option", { name: /Moscow/iu, hidden: true });
    await user.click(document.body);

    expect(onChange).toHaveBeenCalledWith(GEO_CITIES[0]);
    expect(screen.getByLabelText("From")).toHaveValue("Moscow");
  });

  it("если подсказки пришли уже после ухода из поля, название тоже засчитывается", async () => {
    const onChange = vi.fn();
    const { user } = renderWithProviders(
      <CityAutocomplete label="From" placeholder="City" value={null} onChange={onChange} />,
    );

    await user.type(screen.getByLabelText("From"), "Moscow");
    // Leaving right away: neither the debounce nor the response has happened yet.
    await user.click(document.body);

    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith(GEO_CITIES[0]);
    });
  });

  it("неполное название при уходе из поля не засчитывается", async () => {
    const onChange = vi.fn();
    const { user } = renderWithProviders(
      <CityAutocomplete label="From" placeholder="City" value={null} onChange={onChange} />,
    );

    await user.type(screen.getByLabelText("From"), "Mos");
    await screen.findByRole("option", { name: /Moscow/iu, hidden: true });
    await user.click(document.body);

    expect(onChange).not.toHaveBeenCalled();
  });

  it("если у нескольких городов одно название, засчитывается первый из выдачи", async () => {
    const [moscow] = GEO_CITIES;
    const namesake = { ...moscow, cityId: "55555555-5555-4555-8555-555555555555", countryCode: "US" };
    server.use(http.get("/v1/geo/cities/search/", () => HttpResponse.json({ items: [moscow, namesake] })));
    const onChange = vi.fn();
    const { user } = renderWithProviders(
      <CityAutocomplete label="From" placeholder="City" value={null} onChange={onChange} />,
    );

    await user.type(screen.getByLabelText("From"), "Moscow");
    await waitFor(() => {
      expect(screen.getAllByRole("option", { hidden: true })).toHaveLength(2);
    });
    await user.click(document.body);

    expect(onChange).toHaveBeenCalledTimes(1);
    expect(onChange).toHaveBeenCalledWith(moscow);
  });

  it("подтягивает видимый текст при внешней смене value (swap городов в форме)", () => {
    const [moscow, london] = GEO_CITIES;
    const { rerender } = renderWithProviders(
      <CityAutocomplete label="From" placeholder="City" value={moscow} onChange={vi.fn()} />,
    );
    expect(screen.getByLabelText("From")).toHaveValue(moscow.name);

    // The parent changed value not via our onChange: the field must show the new name.
    rerender(<CityAutocomplete label="From" placeholder="City" value={london} onChange={vi.fn()} />);

    expect(screen.getByLabelText("From")).toHaveValue(london.name);
  });

  it("стирание запроса ниже двух символов убирает подсказки", async () => {
    const { user } = renderWithProviders(
      <CityAutocomplete label="From" placeholder="City" value={null} onChange={vi.fn()} />,
    );
    const input = screen.getByLabelText("From");

    await user.type(input, "Mos");
    await screen.findByRole("option", { name: /Moscow/iu, hidden: true });

    await user.clear(input);
    await user.type(input, "M");

    await waitFor(() => {
      expect(screen.queryByRole("option", { name: /Moscow/iu, hidden: true })).not.toBeInTheDocument();
    });
  });

  it("после выбора города повторный поиск по его же имени не уходит в сеть", async () => {
    // The debounce "catches up" with the filled-in name of the picked city; without the guard that
    // would be a needless request whose results would reopen the dropdown over a filled field.
    let requests = 0;
    server.use(
      http.get("/v1/geo/cities/search/", () => {
        requests += 1;
        return HttpResponse.json({ items: GEO_CITIES.filter((city) => city.name === "Moscow") });
      }),
    );
    const { user } = renderWithProviders(
      <CityAutocomplete label="From" placeholder="City" value={null} onChange={vi.fn()} />,
    );

    await user.type(screen.getByLabelText("From"), "Mos");
    await user.click(await screen.findByRole("option", { name: /Moscow/iu, hidden: true }));
    const afterPick = requests;

    // The only way to see the ABSENCE of a request is to let the debounce (250 ms in the component)
    // run on the filled-in name and check the counter did not move.
    await new Promise((resolve) => setTimeout(resolve, DEBOUNCE_SETTLE_MS));

    expect(requests).toBe(afterPick);
  });

  it("показывает подсказку о пустой выдаче, когда ничего не найдено", async () => {
    server.use(http.get("/v1/geo/cities/search/", () => HttpResponse.json({ items: [] })));
    const onChange = vi.fn();
    const { user } = renderWithProviders(
      <CityAutocomplete label="From" placeholder="City" value={null} onChange={onChange} />,
    );

    await user.type(screen.getByLabelText("From"), "Zzz");

    expect(
      await screen.findByText("Nothing found — try another spelling or the English name."),
    ).toBeInTheDocument();
    expect(onChange).not.toHaveBeenCalled();
  });

  it("под названием города — страна на языке интерфейса, неизвестный код — как есть", async () => {
    const unknownCountryCity = { ...GEO_CITIES[0], cityId: "44444444-4444-4444-8444-444444444444", name: "Mosk", countryCode: "XX" };
    server.use(http.get("/v1/geo/cities/search/", () => HttpResponse.json({ items: [GEO_CITIES[0], unknownCountryCity] })));
    const { user } = renderWithProviders(
      <CityAutocomplete label="From" placeholder="City" value={null} onChange={vi.fn()} />,
    );

    await user.type(screen.getByLabelText("From"), "Mos");

    expect(await screen.findByRole("option", { name: /Moscow/iu, hidden: true })).toHaveTextContent("Russia");
    expect(screen.getByRole("option", { name: /Mosk/iu, hidden: true })).toHaveTextContent("XX");
  });
});

import { vi } from "vitest";

/** Makes `method` throw on both storages, as a disabled or full storage does; the setup restores it after the test. */
export function breakStorage(method: "getItem" | "setItem"): void {
  vi.spyOn(Storage.prototype, method).mockImplementation(() => {
    throw new Error(`storage ${method} is unavailable`);
  });
}

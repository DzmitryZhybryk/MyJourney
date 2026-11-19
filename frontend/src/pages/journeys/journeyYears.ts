const YEARS_BACK = 100;

/** Years a journey can have, newest first: from `currentYear` back 100 years. */
export function journeyYearOptions(currentYear: number): readonly string[] {
  return Array.from({ length: YEARS_BACK + 1 }, (_, i) => String(currentYear - i));
}

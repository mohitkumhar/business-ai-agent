import { phoneCountries } from "./phoneCountries.data";
import type { PhoneCountry } from "./phoneCountries.types";

/** Find a country by its ISO code (e.g. "IN", "US") */
export function findByCode(code: string): PhoneCountry | undefined {
  return phoneCountries.find(
    (c) => c.code.toLowerCase() === code.toLowerCase()
  );
}

/** Find a country by its dial code (e.g. "+91") */
export function findByDialCode(dialCode: string): PhoneCountry | undefined {
  return phoneCountries.find((c) => c.dial_code === dialCode);
}

/** Returns a display label e.g. "🇮🇳 India (+91)" */
export function getLabel(country: PhoneCountry): string {
  return `${country.flag} ${country.name}${
    country.dial_code ? ` (${country.dial_code})` : ""
  }`;
}

/** Search countries by name or dial code */
export function searchCountries(query: string): PhoneCountry[] {
  const q = query.toLowerCase().trim();
  if (!q) return phoneCountries;
  return phoneCountries.filter(
    (c) =>
      c.name.toLowerCase().includes(q) ||
      c.dial_code.includes(q)
  );
}
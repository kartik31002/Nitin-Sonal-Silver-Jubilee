import type { PeoplePayload } from "../types";

const DATA_URL = `${import.meta.env.BASE_URL}data/people.json`;

let cached: Promise<PeoplePayload> | null = null;

export function loadPeople(): Promise<PeoplePayload> {
  if (cached === null) {
    cached = fetch(DATA_URL, { cache: "force-cache" })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(
            `Failed to load people.json (${response.status} ${response.statusText}).`,
          );
        }
        return (await response.json()) as PeoplePayload;
      })
      .catch((err) => {
        cached = null;
        throw err;
      });
  }
  return cached;
}

export function resolveAssetUrl(relative: string): string {
  if (/^https?:/i.test(relative) || relative.startsWith("data:")) {
    return relative;
  }
  const trimmed = relative.replace(/^\/+/, "");
  return `${import.meta.env.BASE_URL}${trimmed}`;
}

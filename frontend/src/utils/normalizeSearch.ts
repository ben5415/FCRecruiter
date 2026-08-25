const SPECIAL_CHARACTERS: Record<string, string> = {
  ø: "o",
  ł: "l",
  đ: "d",
  ð: "d",
  þ: "th",
  æ: "ae",
  œ: "oe",
  ß: "ss",
};

/** Normalize European Latin text for case- and accent-insensitive matching. */
export function normalizeSearch(value: string): string {
  return value
    .toLocaleLowerCase()
    .replace(/[øłđðþæœß]/g, (character) => SPECIAL_CHARACTERS[character])
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .trim();
}

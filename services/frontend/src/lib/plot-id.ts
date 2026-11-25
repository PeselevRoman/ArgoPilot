// Next.js gives a page its route parameter still percent-encoded ("a%20b"). The clients encode the
// id again when they build a URL, so the page decodes it once first. Null means the text is not
// valid percent-encoding, and the page treats it as a plot that does not exist.
export function decodePlotId(raw: string): string | null {
  try {
    return decodeURIComponent(raw);
  } catch {
    return null;
  }
}

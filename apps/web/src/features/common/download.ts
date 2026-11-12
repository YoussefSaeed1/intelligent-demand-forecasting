/** Client-side CSV of rows already displayed on the page (bounded, no server call, no new data). */
export const MAX_CSV_ROWS = 2_000;

function cell(value: unknown): string {
  const text = value === null || value === undefined ? "" : String(value);
  // Quote when needed and neutralise spreadsheet formula injection.
  const safe = /^[=+\-@\t\r]/.test(text) && !/^-?\d/.test(text) ? `'${text}` : text;
  return /[",\n]/.test(safe) ? `"${safe.replace(/"/g, '""')}"` : safe;
}

export function toCsv(header: string[], rows: unknown[][], note?: string): string {
  if (rows.length > MAX_CSV_ROWS) throw new Error(`CSV export is limited to ${MAX_CSV_ROWS} rows`);
  const lines = [header.map(cell).join(","), ...rows.map((r) => r.map(cell).join(","))];
  return `${note ? `# ${note}\n` : ""}${lines.join("\n")}\n`;
}

export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1_000);
}

export function downloadText(text: string, filename: string) {
  downloadBlob(new Blob([text], { type: "text/csv;charset=utf-8" }), filename);
}

// CSV export of delivered listings. Titles come from scraped web pages, so cells that start with a formula
// character are neutralised (spreadsheets would otherwise execute them) and quotes are escaped.
const cell = (v) => {
  let s = v == null ? "" : String(v);
  if (/^[=+\-@\t\r]/.test(s)) s = `'${s}`;
  return /[",\n\r]/.test(s) ? `"${s.replaceAll('"', '""')}"` : s;
};

export function toCsv(flats) {
  const head = ["title", "rent_czk", "district", "url"];
  const rows = flats.map((f) => [f.title, f.price_czk, f.district, f.url].map(cell).join(","));
  return [head.join(","), ...rows].join("\r\n");
}

export function sortFlats(flats, key, dir) {
  const sign = dir === "desc" ? -1 : 1;
  return [...flats].sort((a, b) => {
    const x = a[key], y = b[key];
    return (typeof x === "number" && typeof y === "number" ? x - y : String(x).localeCompare(String(y), "cs")) * sign;
  });
}

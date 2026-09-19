// Backend timestamps are UTC: either SQLite datetime format
// ('YYYY-MM-DD HH:MM:SS') or ISO with timezone. Normalize to a
// zoned ISO string so Date parses them as UTC, then render local time.
export const fmtTime = (s) => {
  if (!s) return ''
  const raw = String(s)
  const iso = raw.includes('T')
    ? raw
    : raw.replace(' ', 'T') + 'Z'
  return new Date(iso).toLocaleString()
}

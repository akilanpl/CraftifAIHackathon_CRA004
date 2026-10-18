/** Presentation-only calculations over stored API values. No invented time points. */
export type TrendPoint = {date: string; count: number};
export type TrendPeriod = 'daily' | 'weekly';
export type TimestampedIncident = {timestamp: string; zone_id: string; zone_name: string};
export type NamedZone = {id: string; name: string};

function calendarDay(value: string): number | null {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return null;
  const stamp = Date.parse(`${value}T00:00:00.000Z`);
  return Number.isFinite(stamp) && new Date(stamp).toISOString().slice(0, 10) === value ? stamp : null;
}

export function validIncidentCount(value: unknown): value is number {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0;
}

export function presentIncidentTrend(rows: readonly TrendPoint[], period: TrendPeriod): {points: TrendPoint[]; invalidRows: number} {
  const grouped = new Map<string, number>();
  let invalidRows = 0;
  for (const row of rows) {
    const stamp = calendarDay(row.date);
    if (stamp === null || !validIncidentCount(row.count)) {invalidRows++; continue;}
    const day = new Date(stamp);
    if (period === 'weekly') day.setUTCDate(day.getUTCDate() - (day.getUTCDay() + 6) % 7);
    const key = day.toISOString().slice(0, 10);
    grouped.set(key, (grouped.get(key) ?? 0) + row.count);
  }
  return {points: [...grouped].sort(([a], [b]) => a.localeCompare(b)).map(([date, count]) => ({date, count})), invalidRows};
}

/** Require an explicit offset: never reinterpret a source clock as local browser time. */
export function latestIncidentTimestamp(incidents: readonly {timestamp: string}[]): string | null {
  let latest: number | null = null;
  for (const {timestamp} of incidents) {
    const match = /^(\d{4}-\d{2}-\d{2})T(?:[01]\d|2[0-3]):[0-5]\d(?::[0-5]\d(?:\.\d{1,9})?)?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)$/i.exec(timestamp);
    if (!match || calendarDay(match[1]) === null) continue;
    const stamp = Date.parse(timestamp);
    if (Number.isFinite(stamp) && (latest === null || stamp > latest)) latest = stamp;
  }
  return latest === null ? null : new Date(latest).toISOString();
}

export function presentZoneTotals(totals: Readonly<Record<string, number>>, zones: readonly NamedZone[], incidents: readonly TimestampedIncident[]) {
  return Object.entries(totals).filter(([, count]) => validIncidentCount(count)).map(([key, count]) => {
    const current = zones.find(zone => zone.id === key);
    const historical = incidents.find(incident => incident.zone_id === key);
    return {key, label: current?.name ?? (historical ? `${historical.zone_name} (deleted zone)` : key), count};
  }).sort((a, b) => b.count - a.count || a.label.localeCompare(b.label));
}

export function incidentChartScale(points: readonly TrendPoint[]) {
  const peak = points.reduce((maximum, point) => Math.max(maximum, point.count), 0);
  const step = Math.max(1, Math.ceil((peak + 1) / 4));
  return {maximum: step * 4, ticks: [4, 3, 2, 1, 0].map(value => value * step)};
}

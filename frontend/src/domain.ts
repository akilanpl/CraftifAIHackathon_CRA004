export type NamedZone = { id: string; name: string };
export type IncidentZone = { zone_id: string; zone_name: string };
/** Retained history remains filterable after its zone is deleted. */
export function incidentZoneOptions(zones: NamedZone[], incidents: IncidentZone[]): NamedZone[] {
  const options = new Map(zones.map(zone => [zone.id, { id: zone.id, name: zone.name }]));
  for (const incident of incidents) {
    if (!options.has(incident.zone_id)) options.set(incident.zone_id, { id: incident.zone_id, name: `${incident.zone_name} (deleted zone)` });
  }
  return [...options.values()];
}
/** Coordinates refer to the SVG drawing area inside its border. */
export function normalizedPoint(clientX: number, clientY: number, rect: { left: number; top: number; width: number; height: number }, border = 0): [number, number] {
  const width = Math.max(1, rect.width - 2 * border);
  const height = Math.max(1, rect.height - 2 * border);
  const clamp = (value: number) => Math.max(0, Math.min(1, value));
  return [clamp((clientX - rect.left - border) / width), clamp((clientY - rect.top - border) / height)];
}

export type SourceKind = 'replay' | 'synthetic' | 'live' | 'canonical';
/** Replay is recorded real evidence, never live input or simulated detections. */
export function sourceKind(source?: string, synthetic = false, mode?: string): SourceKind {
  if (synthetic || mode === 'synthetic') return 'synthetic';
  if (source === 'pipegen_replay' || mode === 'replay') return 'replay';
  return source === 'pipegen' ? 'live' : 'canonical';
}
export function relativePtsSeconds(pts?: number | null, first?: number | null): number | null {
  if (pts == null || first == null || !Number.isFinite(pts) || !Number.isFinite(first)) return null;
  return Math.max(0, (pts - first) / 1e9);
}
export function formatRelativePts(pts?: number | null, first?: number | null): string {
  const seconds = relativePtsSeconds(pts, first);
  return seconds == null ? 'PTS unavailable' : `${seconds.toFixed(2)} s`;
}

/** A first observation inside a zone is not evidence of crossing its boundary. */
export function incidentEventLabel(eventType: string, source?: string, synthetic = false, entryBasis?: string): string {
  if (sourceKind(source, synthetic) !== 'replay') return eventType.replace(/_/g, ' ');
  if (entryBasis === 'first_observed_inside') return 'Inside on first observation';
  if (entryBasis === 'observed_outside_to_inside') return 'Observed zone entry';
  return 'Recorded zone alert (basis unavailable)';
}
export function originalTrackId(trackId: string | null, mapping?: Record<string, string>): string | null {
  return trackId == null ? null : mapping?.[trackId] ?? trackId;
}

/** Same boundary-inclusive bottom-center membership convention as the backend. */
export function pointInPolygon(point: readonly number[], polygon: readonly (readonly number[])[]): boolean {
  let inside = false;
  const [x,y] = point;
  for (let i=0,j=polygon.length-1;i<polygon.length;j=i++) {
    const a=polygon[j], b=polygon[i];
    const cross=(x-a[0])*(b[1]-a[1])-(y-a[1])*(b[0]-a[0]);
    if (Math.abs(cross)<1e-10 && x>=Math.min(a[0],b[0])-1e-10 && x<=Math.max(a[0],b[0])+1e-10 && y>=Math.min(a[1],b[1])-1e-10 && y<=Math.max(a[1],b[1])+1e-10) return true;
    if ((a[1]>y)!==(b[1]>y) && x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]) inside=!inside;
  }
  return inside;
}

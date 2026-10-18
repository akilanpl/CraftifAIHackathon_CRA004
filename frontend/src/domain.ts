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

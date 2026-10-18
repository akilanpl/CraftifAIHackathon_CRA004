export type ZonePoint = [number, number];
export type ZoneDefinition = {
  id: string;
  name: string;
  camera_id: string;
  severity: string;
  polygon: number[][];
  confidence_threshold: number;
  debounce_frames?: number;
};
export type ZoneDraft = Omit<ZoneDefinition, 'id' | 'polygon'> & {id?: string; polygon: ZonePoint[]};

export function newZoneDraft(camera: string): ZoneDraft {
  return {name: '', camera_id: camera, severity: 'high', polygon: [], confidence_threshold: .5, debounce_frames: 1};
}

export function copyZoneDraft(zone: ZoneDefinition | ZoneDraft): ZoneDraft {
  return {...zone, debounce_frames: zone.debounce_frames ?? 1, polygon: zone.polygon.map(p => [p[0], p[1]])};
}

const cross = (a: ZonePoint, b: ZonePoint, c: ZonePoint) => (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);
const onSegment = (p: ZonePoint, a: ZonePoint, b: ZonePoint) => Math.abs(cross(a, b, p)) < 1e-10 && p[0] >= Math.min(a[0], b[0]) - 1e-10 && p[0] <= Math.max(a[0], b[0]) + 1e-10 && p[1] >= Math.min(a[1], b[1]) - 1e-10 && p[1] <= Math.max(a[1], b[1]) + 1e-10;
const intersects = (a: ZonePoint, b: ZonePoint, c: ZonePoint, d: ZonePoint) => (cross(a, b, c) * cross(a, b, d) < 0 && cross(c, d, a) * cross(c, d, b) < 0) || onSegment(c, a, b) || onSegment(d, a, b) || onSegment(a, c, d) || onSegment(b, c, d);

/** Match backend constraints without silently clipping numeric input. */
export function polygonError(points: ZonePoint[]): string | null {
  if (points.length < 3) return 'Add at least three vertices to define the zone.';
  if (points.length > 64) return 'A zone can have at most 64 vertices.';
  if (points.some(point => point.length !== 2 || point.some(value => !Number.isFinite(value) || value < 0 || value > 1))) return 'Every X and Y coordinate must be a finite number between 0 and 1.';
  if (new Set(points.map(point => JSON.stringify(point))).size !== points.length) return 'Vertices must be distinct. The polygon closes automatically.';
  for (let i = 0; i < points.length; i++) {
    const previous = points[(i + points.length - 1) % points.length], current = points[i], next = points[(i + 1) % points.length];
    if (onSegment(next, previous, current) || onSegment(previous, current, next)) return 'Adjacent edges cannot overlap or reverse direction.';
  }
  const twiceArea = points.reduce((sum, point, i) => sum + point[0] * points[(i + 1) % points.length][1] - points[(i + 1) % points.length][0] * point[1], 0);
  if (Math.abs(twiceArea) < 1e-8) return 'The polygon must enclose an area.';
  for (let i = 0; i < points.length; i++) {
    for (let j = i + 1; j < points.length; j++) {
      if (j === i + 1 || (i === 0 && j === points.length - 1)) continue;
      if (intersects(points[i], points[(i + 1) % points.length], points[j], points[(j + 1) % points.length])) return 'Polygon edges cannot cross or touch another edge.';
    }
  }
  return null;
}

export function zoneDraftError(draft: ZoneDraft): string | null {
  if (!draft.name.trim()) return 'Enter a zone name.';
  if (draft.name.trim().length > 100) return 'Zone names can contain at most 100 characters.';
  if (!draft.camera_id.trim()) return 'Enter the camera ID that this zone belongs to.';
  if (draft.camera_id.trim().length > 100) return 'Camera IDs can contain at most 100 characters.';
  if (!['low', 'medium', 'high', 'critical'].includes(draft.severity)) return 'Choose a supported severity.';
  if (!Number.isFinite(draft.confidence_threshold) || draft.confidence_threshold < 0 || draft.confidence_threshold > 1) return 'Confidence must be a number between 0 and 1.';
  const debounce = draft.debounce_frames ?? 1;
  if (!Number.isInteger(debounce) || debounce < 1 || debounce > 120) return 'Entry debounce must be a whole number from 1 to 120 frames.';
  return polygonError(draft.polygon);
}

export function zonePayload(draft: ZoneDraft): Omit<ZoneDefinition, 'id'> {
  const error = zoneDraftError(draft);
  if (error) throw new Error(error);
  return {name: draft.name.trim(), camera_id: draft.camera_id.trim(), severity: draft.severity, confidence_threshold: draft.confidence_threshold, debounce_frames: draft.debounce_frames ?? 1, polygon: draft.polygon.map(point => [...point])};
}

export function canvasPoint(clientX: number, clientY: number, bounds: {left: number; top: number; width: number; height: number}): ZonePoint | null {
  if (![clientX, clientY, bounds.left, bounds.top, bounds.width, bounds.height].every(Number.isFinite) || bounds.width <= 0 || bounds.height <= 0) return null;
  const clamp = (value: number) => Math.max(0, Math.min(1, value));
  return [clamp((clientX - bounds.left) / bounds.width), clamp((clientY - bounds.top) / bounds.height)];
}

export function moveVertex(points: ZonePoint[], index: number, next: ZonePoint): ZonePoint[] {
  return points.map((point, i) => i === index ? [...next] : [...point]);
}

export function suggestedVertex(points: ZonePoint[]): ZonePoint {
  const initial: ZonePoint[] = [[.2, .2], [.8, .2], [.8, .8], [.2, .8]];
  if (points.length < initial.length) return [...initial[points.length]];
  const last = points[points.length - 1], first = points[0];
  return [(last[0] + first[0]) / 2, (last[1] + first[1]) / 2];
}

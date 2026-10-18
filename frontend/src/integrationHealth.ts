/** Read-only integration checks and presentation; no ingestion or mode changes. */
export interface IntegrationProfile {state: string; scene_type?: string; name?: string; errors?: string[]}
export interface IntegrationStatus {
  connected?: boolean; mode: string; integration_status: string; source_name: string | null;
  last_event_time: string | null; fps: number | null; inference_latency_ms: number | null;
  gpu_name: string | null; source?: string; errors: string[];
  replay?: {configured: boolean}; profile?: IntegrationProfile;
}
export type AIServiceHealth = {
  available: boolean; engine: string | null; runtimeVersion: string | null; providers: string[];
  reason: string | null; hardwareTest: string; workerBusy: boolean | null;
};
function object(value: unknown): Record<string, unknown> | null {
  return typeof value === 'object' && value !== null && !Array.isArray(value) ? value as Record<string, unknown> : null;
}
function text(value: unknown): string | null {return typeof value === 'string' && value.trim() ? value : null;}

export function parseAIServiceHealth(value: unknown): AIServiceHealth | null {
  const body = object(value), inference = object(body?.inference);
  if (body?.service !== 'independent_ai_monitor' || !inference || typeof inference.available !== 'boolean') return null;
  return {
    available: inference.available, engine: text(inference.engine), runtimeVersion: text(inference.runtime_version),
    providers: Array.isArray(inference.providers) ? inference.providers.filter((provider): provider is string => typeof provider === 'string' && Boolean(provider.trim())) : [],
    reason: text(inference.reason) ?? text(inference.cause),
    hardwareTest: text(body.physical_camera_hardware_test) ?? text(inference.physical_camera_hardware_test) ?? 'Not reported',
    workerBusy: typeof body.worker_busy === 'boolean' ? body.worker_busy : null,
  };
}
export function parseV2ServiceHealth(value: unknown): {mode: string} | null {
  const body = object(value);
  return body?.service === 'Hazard Zone Sentinel' && body.status === 'ok' && typeof body.mode === 'string' ? {mode: body.mode} : null;
}
export function integrationInputLabel(status: IntegrationStatus | null, replay: boolean, synthetic: boolean): string {
  if (!status) return 'Waiting for backend status';
  if (synthetic) return 'SYNTHETIC TEST MODE';
  if (replay) {
    const profile = status.profile;
    const blocked = profile && profile.state !== 'READY' && !(profile.state === 'LEGACY' && profile.scene_type === 'historical_street');
    return blocked ? `DATASET PROFILE · ${profile.state}` : 'RECORDED PIPEGEN REPLAY';
  }
  return status.mode === 'live' ? 'Live / production' : status.mode.replace(/_/g, ' ');
}
export function ingestionBoundary(replay: boolean, synthetic: boolean): {canonical: string; native: string; note: string} {
  if (replay) return {canonical: 'Blocked in replay · HTTP 409', native: 'Blocked in replay · HTTP 409', note: 'Recorded replay rejects live ingestion. Video playback and explicit analysis remain separate.'};
  if (synthetic) return {canonical: 'Synthetic provenance', native: 'Live mode required · HTTP 409', note: 'Canonical input is labeled synthetic. Native PipeGen ingestion requires live mode.'};
  return {canonical: 'Canonical schema', native: 'Configured parser required', note: 'In live mode, native PipeGen ingestion returns HTTP 501 until a genuine-schema parser is configured. This page never changes the backend mode.'};
}
export function integrationTimestamp(timestamp: string | null | undefined): string | null {
  if (!timestamp || !/^\d{4}-\d{2}-\d{2}T(?:[01]\d|2[0-3]):[0-5]\d(?::[0-5]\d(?:\.\d{1,9})?)?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)$/i.test(timestamp)) return null;
  const stamp = Date.parse(timestamp), day = Date.parse(timestamp.slice(0, 10) + 'T00:00:00Z');
  if (!Number.isFinite(stamp) || !Number.isFinite(day) || new Date(day).toISOString().slice(0, 10) !== timestamp.slice(0, 10)) return null;
  return new Date(stamp).toISOString();
}
export function endpointAddress(path: string, origin: string, websocket = false): string {
  if (!path.startsWith('/api/') && !path.startsWith('/ws/')) throw new Error('Expected a local API or WebSocket path');
  const base = new URL(origin);
  if (!['http:', 'https:'].includes(base.protocol)) throw new Error('Expected an HTTP dashboard origin');
  const result = new URL(path, base.origin);
  if (websocket) result.protocol = base.protocol === 'https:' ? 'wss:' : 'ws:';
  return result.toString();
}
export async function readIntegrationJSON(path: string, signal: AbortSignal, fetcher: typeof fetch = fetch): Promise<unknown> {
  const response = await fetcher(path, {method: 'GET', signal, cache: 'no-store', headers: {Accept: 'application/json'}});
  if (!response.ok) throw new Error(`HTTP ${response.status} from ${path}`);
  try {return await response.json();} catch {throw new Error(`Invalid JSON from ${path}`);}
}

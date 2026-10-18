import { useCallback, useEffect, useRef, useState } from 'react';
import { Activity, AlertCircle, Check, CheckCircle2, Copy, Cpu, RefreshCw, ShieldCheck, Unplug } from 'lucide-react';
import { endpointAddress, ingestionBoundary, integrationInputLabel, integrationTimestamp, parseAIServiceHealth, parseV2ServiceHealth, readIntegrationJSON, type AIServiceHealth, type IntegrationStatus } from './integrationHealth';
import './integrationPage.css';
export type {IntegrationStatus} from './integrationHealth';
export interface IntegrationPageProps {status: IntegrationStatus | null; connected: boolean; socketUp: boolean; zonesCount: number; replay: boolean; synthetic: boolean}
type CheckResult = {state: 'checking' | 'ok' | 'error'; error?: string};

export default function IntegrationPage({status, connected, socketUp, zonesCount, replay, synthetic}: IntegrationPageProps) {
  const [checking, setChecking] = useState(false);
  const [v2, setV2] = useState<CheckResult>({state: 'checking'});
  const [aiCheck, setAICheck] = useState<CheckResult>({state: 'checking'});
  const [ai, setAI] = useState<AIServiceHealth | null>(null);
  const [checkedAt, setCheckedAt] = useState<string | null>(null);
  const [copied, setCopied] = useState<string | null>(null);
  const [copyError, setCopyError] = useState<string | null>(null);
  const [copying, setCopying] = useState<string | null>(null);
  const request = useRef(0), controller = useRef<AbortController | null>(null);
  const boundary = ingestionBoundary(replay, synthetic);
  const timestamp = integrationTimestamp(status?.last_event_time);
  const errors = [...new Set([...(status?.errors ?? []), ...(status?.profile?.errors ?? [])])];
  const checkServices = useCallback(async () => {
    controller.current?.abort();
    const active = new AbortController(); controller.current = active;
    const generation = ++request.current;
    setChecking(true); setV2({state: 'checking'}); setAICheck({state: 'checking'}); setAI(null);
    const timeout = window.setTimeout(() => active.abort(), 6000);
    const results = await Promise.allSettled([
      readIntegrationJSON('/api/health', active.signal).then(value => {if (!parseV2ServiceHealth(value)) throw new Error('Unexpected V2 health response');}),
      readIntegrationJSON('/api/ai/status', active.signal).then(value => {const parsed = parseAIServiceHealth(value); if (!parsed) throw new Error('Unexpected independent AI status response'); return parsed;}),
    ]);
    window.clearTimeout(timeout);
    if (request.current !== generation) return;
    const message = (reason: unknown) => reason instanceof Error && reason.name === 'AbortError' ? 'Service check timed out. Retry when the service is available.' : reason instanceof Error ? reason.message : 'Service check failed';
    setV2(results[0].status === 'fulfilled' ? {state: 'ok'} : {state: 'error', error: message(results[0].reason)});
    if (results[1].status === 'fulfilled') {setAI(results[1].value); setAICheck({state: 'ok'});} else setAICheck({state: 'error', error: message(results[1].reason)});
    setCheckedAt(new Date().toISOString()); setChecking(false);
  }, []);
  useEffect(() => {void checkServices(); return () => {request.current++; controller.current?.abort();};}, [checkServices]);
  async function copyEndpoint(path: string, websocket = false) {
    setCopyError(null); setCopied(null); setCopying(path);
    try {
      if (!navigator.clipboard?.writeText) throw new Error('Clipboard unavailable. Select and copy the endpoint text manually.');
      await navigator.clipboard.writeText(endpointAddress(path, window.location.origin, websocket)); setCopied(path);
    } catch (error) {setCopyError(error instanceof Error ? error.message : 'Could not copy the endpoint. Select its text and copy manually.');}
    finally {setCopying(null);}
  }
  const endpoint = (method: string, path: string, caption?: string, websocket = false) => <div className="integration-endpoint-wrap"><div className="integration-endpoint"><code><span>{method}</span> {path}</code><button type="button" onClick={() => void copyEndpoint(path, websocket)} disabled={copying !== null} aria-label={`${copied === path ? 'Copied' : 'Copy'} ${path}`} title={copied === path ? 'Copied endpoint URL' : 'Copy endpoint URL'}>{copied === path ? <Check size={15}/> : <Copy size={15}/>}</button></div>{caption && <small>{caption}</small>}</div>;
  const lastEvent = timestamp ? new Intl.DateTimeFormat('en-GB', {day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23', timeZone: 'UTC'}).format(new Date(timestamp)) + ' UTC' : 'Not available';
  const aiText = aiCheck.state === 'checking' ? 'Checking service…' : aiCheck.state === 'error' ? 'Service unavailable' : ai?.available ? 'Inference available' : 'Inference unavailable';
  return <div className="integration-page">
    <div className="integration-page-grid">
      <section className="integration-surface integration-connection"><div className="integration-section-heading"><div><span>Connection details</span><h2>Pipeline integration</h2></div><Activity size={21}/></div>
        <dl className="integration-facts"><div><dt>V2 backend API</dt><dd><span className={`integration-status-pill ${connected ? 'is-good' : 'is-warning'}`}><i/>{connected ? 'Connected' : 'Disconnected'}</span></dd></div><div><dt>V2 live updates</dt><dd>{socketUp ? 'WebSocket connected' : 'Not connected'}</dd></div><div><dt>PipeGen integration</dt><dd>{status?.integration_status?.replace(/_/g, ' ') || 'Waiting for backend status'}</dd></div><div><dt>Input mode</dt><dd className="integration-mode-value">{integrationInputLabel(status, replay, synthetic)}</dd></div><div><dt>Source name</dt><dd>{status?.source_name || 'Not reported'}</dd></div><div><dt>Configured zones</dt><dd>{Number.isSafeInteger(zonesCount) && zonesCount >= 0 ? zonesCount : 'Not available'}</dd></div><div><dt>Last event</dt><dd>{lastEvent}{replay && <small>Replay session clock</small>}</dd></div><div><dt>GPU</dt><dd>{status?.gpu_name || 'Not reported'}</dd></div></dl>
      </section>
      <section className="integration-surface integration-connect"><div className="integration-section-heading"><h2>Connect your pipeline</h2></div><div className="integration-connect-content"><span className="integration-outline-label">Canonical adapter interface</span><p>Send normalized person detections to the canonical endpoint. The backend evaluates zone entry and publishes persisted incidents.</p>{endpoint('POST', '/api/ingest/detections', boundary.canonical)}<p>Native PipeGen parsing requires a parser configured against its genuine output schema.</p>{endpoint('POST', '/api/ingest/pipegen', boundary.native)}<p className="integration-boundary-note">{boundary.note}</p><p className="integration-small-note">Canonical boxes use normalized [x1, y1, x2, y2]. This application schema is not a claim about PipeGen’s native format.</p><div className="integration-doc-links"><a href="https://github.com/akilanpl/hazard-zone-sentinel/blob/main/docs/canonical-schema.md" target="_blank" rel="noreferrer">Canonical API contract</a><a href="https://github.com/akilanpl/hazard-zone-sentinel/blob/main/docs/pipegen-handoff.md" target="_blank" rel="noreferrer">Native metadata handoff</a></div></div></section>
      <section className="integration-surface integration-health"><div className="integration-section-heading"><div><h2>Service health</h2><p>Check each service independently. A healthy API does not prove source or camera activity.</p></div><button type="button" className="integration-check-button" onClick={() => void checkServices()} disabled={checking}><RefreshCw size={14} className={checking ? 'integration-spin' : ''}/>{checking ? 'Checking…' : 'Check services'}</button></div>
        <div className="integration-health-grid"><div className="integration-health-block"><div className="integration-health-label"><ShieldCheck size={17}/><h3>V2 backend</h3><span className={`integration-status-pill ${v2.state === 'ok' ? 'is-good' : 'is-warning'}`}>{v2.state === 'checking' ? 'Checking…' : v2.state === 'ok' ? 'API healthy' : 'Check failed'}</span></div>{endpoint('GET', '/api/health')}{endpoint('WS', '/ws/live', 'Connection status above belongs to V2 updates only.', true)}{v2.error && <p className="integration-check-error" role="status">{v2.error}</p>}</div><div className="integration-health-block"><div className="integration-health-label"><Cpu size={17}/><h3>Independent AI</h3><span className={`integration-status-pill ${aiCheck.state === 'ok' && ai?.available ? 'is-good' : 'is-warning'}`}>{aiText}</span></div>{endpoint('GET', '/api/ai/status', 'Separate inference service and session database.')}<p className="integration-ai-runtime">{ai?.available ? [ai.engine, ai.runtimeVersion, ...ai.providers].filter(Boolean).join(' · ') || 'Runtime details not reported' : ai?.reason || aiCheck.error || 'Checking the independent service does not start monitoring.'}</p><span className="integration-hardware"><Unplug size={13}/>Physical camera hardware: {ai?.hardwareTest || 'Not reported'}</span>{ai?.available && ai.workerBusy !== null && <p className="integration-small-note">Inference worker {ai.workerBusy ? 'busy' : 'available'} · no camera session is started by this check.</p>}</div></div>
        <div className="integration-check-footer">{checkedAt ? <>Last service check <time dateTime={checkedAt}>{new Intl.DateTimeFormat('en-GB', {hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23',timeZone:'UTC'}).format(new Date(checkedAt))} UTC</time></> : 'Waiting for the first service response'}</div>
      </section>
      <section className="integration-surface integration-warnings"><div className="integration-section-heading"><h2>System errors</h2><span className="integration-outline-label">{status ? `${errors.length} reported` : 'Status unavailable'}</span></div>{errors.length ? <ul className="integration-error-list">{errors.map((error,index) => <li key={`${index}-${error}`}><AlertCircle size={16}/><span>{error}</span></li>)}</ul> : <div className="integration-error-empty">{status ? <CheckCircle2 size={18}/> : <AlertCircle size={18}/>}<p>{status ? connected ? 'No system errors reported by the Warehouse V2 backend' : 'Last received report contained no system errors' : 'Waiting for backend status'}{!connected && <span> · V2 backend connection unavailable</span>}</p></div>}{copyError && <p className="integration-copy-error" role="alert"><AlertCircle size={15}/>{copyError}</p>}{copied && <span className="integration-sr-only" role="status">Endpoint URL copied: {copied}</span>}</section>
    </div>
  </div>;
}

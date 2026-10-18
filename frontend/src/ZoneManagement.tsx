import {useEffect, useId, useRef, useState, type KeyboardEvent} from 'react';
import {Check, Crosshair, MapPin, Pencil, Pentagon, Plus, Trash2, X} from 'lucide-react';
import {canvasPoint, copyZoneDraft, moveVertex, newZoneDraft, polygonError, suggestedVertex, zoneDraftError, zonePayload, type ZoneDefinition, type ZoneDraft, type ZonePoint} from './zoneEditor';
import './zoneManagement.css';

type Props = {zones: ZoneDefinition[]; busy: boolean; act: (fn: () => Promise<unknown>) => Promise<void>; camera: string};

async function zoneRequest<T>(path: string, options: RequestInit): Promise<T> {
  const response = await fetch('/api' + path, {...options, headers: {'Content-Type': 'application/json', ...options.headers}});
  if (!response.ok) {
    let message = `Zone request failed (${response.status})`;
    try {const body = await response.json(); message = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail ?? body);} catch { /* Preserve HTTP error when no JSON was returned. */ }
    throw new Error(message);
  }
  return response.status === 204 ? undefined as T : response.json();
}

export default function ZoneManagement({zones, busy, act, camera}: Props) {
  const [draft, setDraft] = useState<ZoneDraft>(() => newZoneDraft(camera));
  const [editing, setEditing] = useState(false), [selected, setSelected] = useState<ZoneDefinition | null>(null);
  const [feedback, setFeedback] = useState('');
  const [localError, setLocalError] = useState(''), [pendingDelete, setPendingDelete] = useState<ZoneDefinition | null>(null);
  const [activeVertex, setActiveVertex] = useState<number | null>(null);
  const canvas = useRef<SVGSVGElement>(null), drag = useRef<number | null>(null);
  const previousIds = useRef(new Set(zones.map(zone => zone.id)));
  const dialog = useRef<HTMLElement>(null), cancelDelete = useRef<HTMLButtonElement>(null);
  const namespace = useId().replace(/:/g, ''), errorId = `${namespace}-error`, polygonHelpId = `${namespace}-polygon-help`;
  const displayed = selected ? zones.find(zone => zone.id === selected.id) ?? selected : null;

  useEffect(() => {
    const current = new Set(zones.map(zone => zone.id));
    if (selected && previousIds.current.has(selected.id) && !current.has(selected.id)) {
      setSelected(null); setEditing(false); setDraft(newZoneDraft(camera)); setLocalError('');
    }
    previousIds.current = current;
  }, [zones, selected, camera]);

  useEffect(() => {
    if (!pendingDelete) return;
    const previous = document.activeElement as HTMLElement | null;
    cancelDelete.current?.focus();
    const keydown = (event: globalThis.KeyboardEvent) => {
      if (event.key === 'Escape' && !busy) setPendingDelete(null);
      if (event.key !== 'Tab') return;
      const buttons = Array.from(dialog.current?.querySelectorAll<HTMLButtonElement>('button:not(:disabled)') ?? []);
      const first = buttons[0], last = buttons[buttons.length - 1];
      if (!first) return;
      if (event.shiftKey && document.activeElement === first) {event.preventDefault(); last.focus();}
      else if (!event.shiftKey && document.activeElement === last) {event.preventDefault(); first.focus();}
    };
    document.addEventListener('keydown', keydown);
    return () => {document.removeEventListener('keydown', keydown); if (previous?.isConnected) previous.focus();};
  }, [pendingDelete, busy]);

  const change = (next: Partial<ZoneDraft>) => {setDraft(value => ({...value, ...next})); setLocalError('');};
  const beginNew = () => {setFeedback(''); setDraft(newZoneDraft(camera)); setEditing(true); setActiveVertex(null); setLocalError('');};
  const beginEdit = (zone: ZoneDefinition) => {setFeedback(''); setSelected(zone); setDraft(copyZoneDraft(zone)); setEditing(true); setActiveVertex(null); setLocalError('');};
  const cancel = () => {setFeedback('Draft discarded. Saved zone unchanged.'); setEditing(false); setDraft(newZoneDraft(camera)); setActiveVertex(null); setLocalError(''); drag.current = null;};
  const save = async () => {
    const error = zoneDraftError(draft);
    if (error) {setLocalError(error); return;}
    await act(async () => {
      const saved = await zoneRequest<ZoneDefinition>(draft.id ? `/zones/${encodeURIComponent(draft.id)}` : '/zones', {method: draft.id ? 'PUT' : 'POST', body: JSON.stringify(zonePayload(draft))});
      setFeedback(`Saved “${saved.name}”.`); setSelected(saved); setEditing(false); setDraft(newZoneDraft(camera)); setLocalError(''); setActiveVertex(null);
    });
  };
  const remove = async () => {
    if (!pendingDelete) return;
    const removedId = pendingDelete.id;
    await act(async () => {
      await zoneRequest(`/zones/${encodeURIComponent(removedId)}`, {method: 'DELETE'});
      setPendingDelete(null);
      if (selected?.id === removedId) {setSelected(null); cancel();}
      setFeedback('Zone deleted. Existing incident history retained.');
    });
  };
  const addVertex = (point?: ZonePoint) => {
    if (draft.polygon.length >= 64) {setLocalError('A zone can have at most 64 vertices.'); return;}
    const next = point ?? suggestedVertex(draft.polygon);
    change({polygon: [...draft.polygon, next]}); setActiveVertex(draft.polygon.length);
  };
  const numeric = (value: string) => value === '' ? NaN : Number(value);
  const vertexKey = (event: KeyboardEvent<SVGCircleElement>, index: number) => {
    if (!editing || busy) return;
    if (event.key === 'Delete' || event.key === 'Backspace') {event.preventDefault(); change({polygon: draft.polygon.filter((_, i) => i !== index)}); setActiveVertex(null); return;}
    const vector: Record<string, ZonePoint> = {ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1]};
    if (!vector[event.key]) return;
    event.preventDefault(); const step = event.shiftKey ? .05 : .01, point = draft.polygon[index], delta = vector[event.key];
    change({polygon: moveVertex(draft.polygon, index, [Math.max(0, Math.min(1, point[0] + delta[0] * step)), Math.max(0, Math.min(1, point[1] + delta[1] * step))])});
  };
  const preview = editing ? draft.polygon : displayed?.polygon ?? [];
  const finitePreview = preview.every(point => point.length === 2 && point.every(Number.isFinite));
  const shapeIssue = editing && draft.polygon.length >= 3 ? polygonError(draft.polygon) : null;

  return <div className="zone-management-page">
    {feedback && <p className="zm-feedback" role="status"><Check size={16}/>{feedback}</p>}
    <div className="zm-layout">
      <section className="zm-pane" aria-labelledby={`${namespace}-zones-heading`}>
        <div className="zm-pane-heading"><h2 id={`${namespace}-zones-heading`}>Your zones <span className="zm-count">{zones.length}</span></h2><button className="zm-button zm-primary" disabled={busy || editing} onClick={beginNew}><Plus size={17}/>New zone</button></div>
        <div className="zm-zone-list">
          {zones.map(zone => <article key={zone.id} className={`zm-zone-card ${selected?.id === zone.id ? 'is-selected' : ''}`}>
            <button className="zm-card-main" disabled={busy || editing} aria-pressed={selected?.id === zone.id} aria-label={`Select ${zone.name}`} onClick={() => {setSelected(zone); setLocalError('');}}>
              <span className="zm-zone-icon"><Pentagon size={29}/></span><span className="zm-card-name"><strong>{zone.name}</strong><small>{zone.camera_id} <span aria-hidden="true">·</span> {zone.polygon.length} vertices</small></span><span className={`zm-severity zm-severity-${zone.severity}`}>{zone.severity}</span>
            </button>
            <div className="zm-card-footer"><span>Confidence ≥ {Math.round(zone.confidence_threshold * 100)}%</span><div><button className="zm-icon-button" disabled={busy || editing} aria-label={`Edit ${zone.name}`} onClick={() => beginEdit(zone)}><Pencil size={19}/></button><button className="zm-icon-button zm-danger-icon" disabled={busy || editing} aria-label={`Delete ${zone.name}`} onClick={() => setPendingDelete(zone)}><Trash2 size={19}/></button></div></div>
          </article>)}
          {!zones.length && <div className="zm-empty zm-list-empty"><span className="zm-empty-icon"><Pentagon size={29}/></span><h3>No restricted zones yet</h3><p>Create a zone to define an area that needs attention.</p><button className="zm-button" disabled={busy || editing} onClick={beginNew}><Plus size={16}/>Create your first zone</button></div>}
        </div>
      </section>
      <section className="zm-pane zm-workspace" aria-labelledby={`${namespace}-workspace-heading`}>
        <div className="zm-pane-heading"><h2 id={`${namespace}-workspace-heading`}>{editing ? draft.id ? 'Edit zone' : 'Create zone' : displayed ? displayed.name : 'Zone workspace'}</h2>{editing ? <button className="zm-icon-button" disabled={busy} aria-label="Cancel editing" onClick={cancel}><X size={19}/></button> : displayed && <button className="zm-button" disabled={busy} onClick={() => beginEdit(displayed)}><Pencil size={16}/>Edit zone</button>}</div>
        {!editing && !displayed ? <div className="zm-empty"><span className="zm-empty-icon"><MapPin size={31}/></span><h3>Make safety boundaries visible</h3><p>Create a zone or select an existing one to edit its polygon<br className="zm-desktop-break"/> and detection settings.</p></div> : <div className="zm-workspace-body">
          {editing && <div className="zm-form-grid">
            <label>Zone name<input autoFocus maxLength={100} value={draft.name} disabled={busy} onChange={event => change({name: event.target.value})} placeholder="e.g. Forklift operating area"/></label>
            <label>Camera ID<input maxLength={100} value={draft.camera_id} disabled={busy} onChange={event => change({camera_id: event.target.value})} placeholder="e.g. warehouse-01"/></label>
            <label>Severity<select value={draft.severity} disabled={busy} onChange={event => change({severity: event.target.value})}>{['low', 'medium', 'high', 'critical'].map(severity => <option key={severity} value={severity}>{severity.charAt(0).toUpperCase() + severity.slice(1)}</option>)}</select></label>
            <label>Confidence threshold<input type="number" min="0" max="1" step="0.05" value={Number.isFinite(draft.confidence_threshold) ? draft.confidence_threshold : ''} disabled={busy} onChange={event => change({confidence_threshold: numeric(event.target.value)})}/></label>
            <label>Entry debounce <span className="zm-label-note">(frames)</span><input type="number" min="1" max="120" step="1" value={Number.isFinite(draft.debounce_frames ?? 1) ? draft.debounce_frames ?? 1 : ''} disabled={busy} onChange={event => change({debounce_frames: numeric(event.target.value)})}/></label>
          </div>}
          {!editing && displayed && <dl className="zm-zone-summary"><div><dt>Camera</dt><dd>{displayed.camera_id}</dd></div><div><dt>Severity</dt><dd><span className={`zm-severity zm-severity-${displayed.severity}`}>{displayed.severity}</span></dd></div><div><dt>Confidence</dt><dd>≥ {Math.round(displayed.confidence_threshold * 100)}%</dd></div><div><dt>Entry debounce</dt><dd>{displayed.debounce_frames ?? 1} frame{(displayed.debounce_frames ?? 1) !== 1 ? 's' : ''}</dd></div></dl>}
          <div className="zm-canvas-caption"><span><Crosshair size={14}/>{editing ? 'Polygon editor' : 'Zone preview'}</span><span>Normalized coordinates · no video preview</span></div>
          <div className="zm-canvas-wrap"><svg ref={canvas} viewBox="0 0 1000 562.5" preserveAspectRatio="none" aria-label={editing ? 'Restricted zone polygon editor' : 'Restricted zone polygon preview'} aria-describedby={editing ? polygonHelpId : undefined} onPointerDown={event => {if (!editing || busy || event.target !== canvas.current) return; const point = canvasPoint(event.clientX, event.clientY, event.currentTarget.getBoundingClientRect()); if (point) addVertex(point);}} onPointerMove={event => {if (!editing || busy || drag.current === null) return; const point = canvasPoint(event.clientX, event.clientY, event.currentTarget.getBoundingClientRect()); if (point) change({polygon: moveVertex(draft.polygon, drag.current, point)});}} onPointerUp={() => {drag.current = null;}} onPointerCancel={() => {drag.current = null;}}>
            <defs><pattern id={`${namespace}-grid`} width="50" height="50" patternUnits="userSpaceOnUse"><path d="M50 0H0V50" fill="none" stroke="#dde5ee" strokeWidth="1"/></pattern></defs><rect width="1000" height="562.5" fill={`url(#${namespace}-grid)`} pointerEvents="none"/>
            {finitePreview && preview.length > 1 && <polygon points={preview.map(point => `${point[0] * 1000},${point[1] * 562.5}`).join(' ')} className={shapeIssue ? 'zm-polygon is-invalid' : 'zm-polygon'} pointerEvents="none"/>}
            {finitePreview && preview.map((point, index) => <g key={index}><circle cx={point[0] * 1000} cy={point[1] * 562.5} r={editing ? 11 : 6} className={activeVertex === index ? 'zm-vertex is-active' : 'zm-vertex'} tabIndex={editing && !busy ? 0 : undefined} role={editing ? 'button' : undefined} aria-label={editing ? `Vertex ${index + 1}, X ${point[0].toFixed(3)}, Y ${point[1].toFixed(3)}. Arrow keys move, Delete removes.` : undefined} onFocus={() => {if (editing) setActiveVertex(index);}} onKeyDown={event => vertexKey(event, index)} onPointerDown={event => {if (!editing || busy) return; event.stopPropagation(); canvas.current?.setPointerCapture(event.pointerId); drag.current = index; setActiveVertex(index);}}/><text x={point[0] * 1000 + 16} y={point[1] * 562.5 - 13} pointerEvents="none">{index + 1}</text></g>)}
          </svg>{!preview.length && <div className="zm-canvas-empty" aria-hidden="true"><Pentagon size={28}/><span>Click to place the first vertex</span></div>}</div>
          {editing ? <>
            <p className="zm-editor-help" id={polygonHelpId}>Click to add points; drag a vertex to adjust it. Use the coordinate fields or arrow keys for precise placement.</p>
            <div className="zm-vertices-heading"><strong>{draft.polygon.length} vertices</strong><div><button className="zm-text-button" disabled={busy || draft.polygon.length >= 64} onClick={() => addVertex()}><Plus size={14}/>Add vertex</button><button className="zm-text-button" disabled={busy || !draft.polygon.length} onClick={() => {change({polygon: []}); setActiveVertex(null);}}>Clear</button></div></div>
            {!!draft.polygon.length && <ol className="zm-coordinate-list" aria-label="Polygon vertex coordinates">{draft.polygon.map((point, index) => <li key={index}><span className="zm-vertex-number">{index + 1}</span>{(['X', 'Y'] as const).map((axis, coordinate) => <label key={axis}>{axis}<input aria-label={`Vertex ${index + 1} ${axis} coordinate`} type="number" min="0" max="1" step="0.001" value={Number.isFinite(point[coordinate]) ? point[coordinate] : ''} disabled={busy} aria-invalid={!Number.isFinite(point[coordinate]) || point[coordinate] < 0 || point[coordinate] > 1} onFocus={() => setActiveVertex(index)} onChange={event => {const next = [...point] as ZonePoint; next[coordinate] = numeric(event.target.value); change({polygon: moveVertex(draft.polygon, index, next)});}}/></label>)}<button className="zm-icon-button" disabled={busy} aria-label={`Remove vertex ${index + 1}`} onClick={() => {change({polygon: draft.polygon.filter((_, i) => i !== index)}); setActiveVertex(null);}}><X size={16}/></button></li>)}</ol>}
            {(localError || shapeIssue) && <p className="zm-form-error" role="alert" id={errorId}>{localError || shapeIssue}</p>}
            <p className="zm-analysis-note">Zone edits change application-computed incident rules. Original detections and existing incident history are retained. Screen-relative demonstration; not a calibrated physical safety boundary.</p>
            <div className="zm-editor-actions"><button className="zm-button" disabled={busy} onClick={cancel}>Cancel</button><button className="zm-button zm-primary" disabled={busy} aria-describedby={localError || shapeIssue ? errorId : undefined} onClick={() => void save()}><Check size={16}/>{busy ? 'Saving…' : 'Save zone'}</button></div>
          </> : <p className="zm-analysis-note">The polygon uses normalized coordinates and adapts to its source frame. Editing it changes application incident rules, not the original detections. Screen-relative demonstration; not a calibrated physical safety boundary.</p>}
        </div>}
      </section>
    </div>
    {pendingDelete && <div className="zm-dialog-backdrop" onClick={event => {if (event.target === event.currentTarget && !busy) setPendingDelete(null);}}><section className="zm-dialog" ref={dialog} role="alertdialog" aria-modal="true" aria-labelledby={`${namespace}-delete-title`} aria-describedby={`${namespace}-delete-description`}><span className="zm-delete-icon"><Trash2 size={24}/></span><h2 id={`${namespace}-delete-title`}>Delete restricted zone?</h2><p id={`${namespace}-delete-description`}>Delete “{pendingDelete.name}”? Existing incident history will be retained. Future frames will no longer be evaluated against this zone.</p><div className="zm-dialog-actions"><button ref={cancelDelete} className="zm-button" disabled={busy} onClick={() => setPendingDelete(null)}>Cancel deletion</button><button className="zm-button zm-delete-button" disabled={busy} onClick={() => void remove()}>{busy ? 'Deleting…' : 'Delete zone'}</button></div></section></div>}
  </div>;
}

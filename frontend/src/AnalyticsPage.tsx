import { useMemo, useState } from 'react';
import { Check, CalendarDays, ChartNoAxesCombined, Clock, Layers3 } from 'lucide-react';
import { incidentChartScale, latestIncidentTimestamp, presentIncidentTrend, presentZoneTotals, validIncidentCount, type TrendPeriod, type TimestampedIncident, type NamedZone } from './analyticsPresentation';
import './analyticsPage.css';

export type AnalyticsSummary = {
  total_incidents: number; acknowledged: number; by_severity: Record<string, number>;
  by_zone: Record<string, number>; trend: {date: string; count: number}[];
};
export type AnalyticsPageProps = {
  analytics: AnalyticsSummary | null; incidents: readonly TimestampedIncident[]; zones: readonly NamedZone[];
  replay: boolean; activeIntrusions: number; sessionIncidents: number;
};
const severityLevels = ['critical', 'high', 'medium', 'low'] as const;
const countText = (value: unknown) => validIncidentCount(value) ? value.toLocaleString('en-GB') : '—';

export default function AnalyticsPage({analytics, incidents, zones, replay, activeIntrusions, sessionIncidents}: AnalyticsPageProps) {
  const [period, setPeriod] = useState<TrendPeriod>('daily');
  const trend = useMemo(() => presentIncidentTrend(analytics?.trend ?? [], period), [analytics, period]);
  const scale = incidentChartScale(trend.points);
  const zoneTotals = useMemo(() => presentZoneTotals(analytics?.by_zone ?? {}, zones, incidents), [analytics, zones, incidents]);
  const latest = useMemo(() => latestIncidentTimestamp(incidents), [incidents]);
  const total = analytics?.total_incidents;
  const acknowledged = analytics?.acknowledged;
  const remaining = validIncidentCount(total) && validIncidentCount(acknowledged) ? Math.max(0, total - acknowledged) : null;
  const timeText = latest ? new Intl.DateTimeFormat('en-GB', {hour: '2-digit', minute: '2-digit', hourCycle: 'h23', timeZone: 'UTC'}).format(new Date(latest)) : '—';
  const dateText = latest ? new Intl.DateTimeFormat('en-GB', {day: '2-digit', month: 'short', year: 'numeric', timeZone: 'UTC'}).format(new Date(latest)) : 'No incidents recorded';
  const chartSummary = trend.points.map(point => `${period === 'weekly' ? 'Week of ' : ''}${point.date}: ${point.count}`).join('; ');

  return <div className="analytics-page">
    <div className="analytics-kpis" aria-label="Incident analytics summary">
      <section className="analytics-kpi"><div><span>{replay ? 'Computed replay alerts' : 'Total incidents'}</span><ChartNoAxesCombined size={16}/></div><strong>{countText(total)}</strong><small>{replay ? 'Persisted across replay sessions' : 'Persisted incident history'}</small></section>
      <section className="analytics-kpi"><div><span>{replay ? 'Analysis occupancy' : 'Active intrusions'}</span><Layers3 size={16}/></div><strong>{countText(activeIntrusions)}</strong><small>{replay ? 'Separate analysis frames, not video' : 'Currently reported zone occupancy'}</small></section>
      <section className="analytics-kpi"><div><span>Session alerts</span><CalendarDays size={16}/></div><strong>{countText(sessionIncidents)}</strong><small>{replay ? 'Current replay analysis session' : 'Current monitoring session'}</small></section>
      <section className="analytics-kpi analytics-kpi-time"><div><span>Last incident</span><Clock size={16}/></div><strong>{latest ? <time dateTime={latest}>{timeText}<span>UTC</span></time> : '—'}</strong><small>{dateText}{latest && replay ? ' · replay session clock' : ''}</small></section>
    </div>
    <div className="analytics-main-grid">
      <section className="analytics-card analytics-trend">
        <div className="analytics-card-heading"><div><span>Persisted events</span><h2>Incident trend</h2></div><label className="analytics-period"><span className="analytics-sr-only">Incident trend grouping</span><select aria-label="Incident trend grouping" value={period} onChange={event => setPeriod(event.target.value as TrendPeriod)}><option value="daily">Daily counts</option><option value="weekly">Weekly counts</option></select></label></div>
        {analytics === null ? <div className="analytics-empty"><ChartNoAxesCombined size={24}/><h3>Analytics unavailable</h3><p>Waiting for stored incident totals from the backend.</p></div> : trend.points.length ? <>
          <div className="analytics-chart" role="img" aria-label={`${period === 'weekly' ? 'Weekly' : 'Daily'} stored incident counts. ${chartSummary}`}>
            <div className="analytics-y-axis" aria-hidden="true">{scale.ticks.map(tick => <span key={tick}>{tick}</span>)}</div>
            <div className="analytics-plot"><div className="analytics-grid-lines" aria-hidden="true">{scale.ticks.map(tick => <i key={tick}/>)}</div><div className="analytics-bars">{trend.points.map(point => <div className="analytics-bar-column" key={point.date}><div className="analytics-bar-well"><div className="analytics-bar" style={{height: `${point.count / scale.maximum * 100}%`}} title={`${period === 'weekly' ? 'Week of ' : ''}${point.date}: ${point.count} incidents`}><strong>{point.count}</strong></div></div><small>{period === 'weekly' && <span>Week of </span>}{point.date}</small></div>)}</div></div>
          </div>
          <details className="analytics-data-table"><summary>View {period} data</summary><table><caption>{period === 'weekly' ? 'Weeks beginning Monday, UTC' : 'Daily totals as reported by the API'}</caption><thead><tr><th>{period === 'weekly' ? 'Week beginning (UTC)' : 'Date'}</th><th>Incidents</th></tr></thead><tbody>{trend.points.map(point => <tr key={point.date}><td>{point.date}</td><td>{point.count}</td></tr>)}</tbody></table></details>
        </> : <div className="analytics-empty"><ChartNoAxesCombined size={24}/><h3>No incident trend yet</h3><p>Stored incident totals will appear when dated events are available.</p></div>}
        {period === 'weekly' && <p className="analytics-chart-note">Weeks begin Monday (UTC). Only reported dates are included.</p>}
        {trend.invalidRows > 0 && <p className="analytics-data-warning" role="status">{trend.invalidRows} invalid trend {trend.invalidRows === 1 ? 'record was' : 'records were'} excluded.</p>}
      </section>
      <section className="analytics-card analytics-severity"><div className="analytics-card-heading"><h2>Severity distribution</h2></div><div className="analytics-severity-list">{severityLevels.map(severity => {
        const count = analytics?.by_severity[severity];
        return <div className={`analytics-distribution-row analytics-severity-${severity}`} key={severity}><div><span><i/>{severity.charAt(0).toUpperCase() + severity.slice(1)}</span><strong>{analytics ? countText(count ?? 0) : '—'}</strong></div><progress aria-label={`${severity} severity incidents`} aria-valuetext={analytics ? `${countText(count ?? 0)} stored incidents` : 'Not available'} max={validIncidentCount(total) && total > 0 ? total : 1} value={validIncidentCount(count) ? count : 0}/></div>;
      })}</div><div className="analytics-ack-summary"><Check size={19}/><div><strong>{analytics ? `${countText(acknowledged)} incidents acknowledged` : 'Acknowledgment totals unavailable'}</strong><span>{remaining === null ? 'Waiting for incident totals' : `${remaining.toLocaleString('en-GB')} awaiting acknowledgment`}</span></div></div></section>
      <section className="analytics-card analytics-zones"><div className="analytics-card-heading"><div><h2>Incidents by zone</h2><p>Totals from persisted incident history</p></div><span className="analytics-zone-count">{analytics ? `${zoneTotals.length} ${zoneTotals.length === 1 ? 'zone' : 'zones'}` : 'Awaiting data'}</span></div>{zoneTotals.length ? <div className="analytics-zone-list">{zoneTotals.map(zone => <div className="analytics-zone-row" key={zone.key}><span title={zone.label}>{zone.label}</span><div><div><strong>{zone.count.toLocaleString('en-GB')}</strong></div><progress aria-label={`${zone.label} incidents`} max={validIncidentCount(total) && total > 0 ? total : Math.max(1, ...zoneTotals.map(item => item.count))} value={zone.count}/></div></div>)}</div> : <div className="analytics-empty analytics-empty-compact"><h3>{analytics ? 'No zone activity yet' : 'Zone totals unavailable'}</h3><p>{analytics ? 'Zone counts will appear after a stored incident.' : 'Waiting for analytics from the backend.'}</p></div>}</section>
    </div>
  </div>;
}

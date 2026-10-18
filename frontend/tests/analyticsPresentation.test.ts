import test from 'node:test';
import assert from 'node:assert/strict';
import { incidentChartScale, latestIncidentTimestamp, presentIncidentTrend, presentZoneTotals, validIncidentCount } from '../src/analyticsPresentation.ts';

test('daily counts sort actual dates and combine supplied totals without inserting missing days', () => {
  const rows = [{date:'2026-10-18',count:2},{date:'2026-10-02',count:1},{date:'2026-10-18',count:3}];
  const original = JSON.stringify(rows);
  assert.deepEqual(presentIncidentTrend(rows,'daily'), {points:[{date:'2026-10-02',count:1},{date:'2026-10-18',count:5}],invalidRows:0});
  assert.equal(JSON.stringify(rows), original);
});
test('Monday UTC weeks include Sunday in the preceding week and preserve Monday boundary', () => {
  assert.deepEqual(presentIncidentTrend([
    {date:'2026-10-18',count:2}, // Sunday
    {date:'2026-10-12',count:3}, // Monday
    {date:'2026-10-19',count:1}, // next Monday
  ],'weekly').points,[{date:'2026-10-12',count:5},{date:'2026-10-19',count:1}]);
});
test('weekly grouping crosses month/year boundaries deterministically', () => {
  assert.deepEqual(presentIncidentTrend([
    {date:'2026-01-01',count:4},{date:'2025-12-29',count:2},{date:'2026-01-04',count:1},{date:'2026-01-05',count:3},
  ],'weekly').points,[{date:'2025-12-29',count:7},{date:'2026-01-05',count:3}]);
});
test('empty trends stay empty and genuine zero observations are retained', () => {
  assert.deepEqual(presentIncidentTrend([],'weekly'), {points:[],invalidRows:0});
  assert.deepEqual(presentIncidentTrend([{date:'2026-10-18',count:0}],'daily').points,[{date:'2026-10-18',count:0}]);
});
test('weekly gaps do not generate synthetic time points', () => {
  const points = presentIncidentTrend([{date:'2026-01-01',count:2},{date:'2026-03-02',count:4}],'weekly').points;
  assert.deepEqual(points,[{date:'2025-12-29',count:2},{date:'2026-03-02',count:4}]);
  assert.equal(points.reduce((sum,p) => sum+p.count,0),6);
});
test('invalid calendar dates, malformed periods and non-count values are reported and excluded', () => {
  const rows = [
    {date:'2026-02-29',count:1},{date:'2026-04-31',count:1},{date:'2026-1-02',count:1},
    {date:'2026-10-18T00:00:00Z',count:1},{date:'2026-10-18',count:-1},
    {date:'2026-10-18',count:NaN},{date:'2026-10-18',count:Infinity},{date:'2026-10-18',count:1.5},
    {date:'2024-02-29',count:2},
  ];
  assert.deepEqual(presentIncidentTrend(rows,'daily'), {points:[{date:'2024-02-29',count:2}],invalidRows:8});
});
test('count validation distinguishes unknown and malformed values from a measured zero', () => {
  assert.equal(validIncidentCount(0),true);
  assert.equal(validIncidentCount(12),true);
  for (const value of [undefined,null,'2',NaN,Infinity,-1,1.5,Number.MAX_SAFE_INTEGER+1]) assert.equal(validIncidentCount(value),false);
});
test('latest timestamp compares actual instants across timezone offsets rather than lexical order', () => {
  assert.equal(latestIncidentTimestamp([
    {timestamp:'2026-10-18T23:59:00+05:30'}, // 18:29 UTC
    {timestamp:'2026-10-18T19:00:00Z'},
    {timestamp:'2026-10-18T14:30:00-04:00'}, // 18:30 UTC
  ]),'2026-10-18T19:00:00.000Z');
});
test('latest timestamp handles UTC day transitions and fractional seconds', () => {
  assert.equal(latestIncidentTimestamp([
    {timestamp:'2026-10-19T00:15:00+05:30'},
    {timestamp:'2026-10-18T23:59:59.123456+00:00'},
  ]),'2026-10-18T23:59:59.123Z');
});
test('timezone-naive, impossible or malformed timestamps never become a guessed local time', () => {
  assert.equal(latestIncidentTimestamp([
    {timestamp:'not a timestamp'},{timestamp:'2026-02-30T12:00:00Z'},
    {timestamp:'2026-10-18T24:00:00Z'},{timestamp:'2026-10-18T12:00:00'},
    {timestamp:'2026-10-18'},{timestamp:'2026-10-18T12:00:00+99:99'},
  ]),null);
  assert.equal(latestIncidentTimestamp([]),null);
});
test('epoch zero is a real latest incident and source rows remain unchanged', () => {
  const rows = [{timestamp:'1969-12-31T23:59:59Z'},{timestamp:'1970-01-01T00:00:00Z'}];
  const original = JSON.stringify(rows);
  assert.equal(latestIncidentTimestamp(rows),'1970-01-01T00:00:00.000Z');
  assert.equal(JSON.stringify(rows),original);
});
test('zone totals support API name keys, current IDs, deleted historical IDs and stable count order', () => {
  const totals = {'active-id':2,'deleted-id':1,'Recorded zone name':3};
  assert.deepEqual(presentZoneTotals(totals,[{id:'active-id',name:'Current zone name'}],[{timestamp:'2026-10-18T00:00:00Z',zone_id:'deleted-id',zone_name:'Historical area'}]),[
    {key:'Recorded zone name',label:'Recorded zone name',count:3},
    {key:'active-id',label:'Current zone name',count:2},
    {key:'deleted-id',label:'Historical area (deleted zone)',count:1},
  ]);
  assert.deepEqual(totals,{'active-id':2,'deleted-id':1,'Recorded zone name':3});
});
test('distinct zone IDs are not merged merely because they currently share a name', () => {
  const rows = presentZoneTotals({a:1,b:1},[{id:'a',name:'Aisle'},{id:'b',name:'Aisle'}],[]);
  assert.equal(rows.length,2);
  assert.equal(rows.reduce((sum,row) => sum+row.count,0),2);
});
test('chart ticks are integer-scaled and never imply padded incident records', () => {
  assert.deepEqual(incidentChartScale([{date:'2026-10-18',count:2}]),{maximum:4,ticks:[4,3,2,1,0]});
  assert.deepEqual(incidentChartScale([{date:'2026-10-18',count:9}]),{maximum:12,ticks:[12,9,6,3,0]});
  assert.deepEqual(incidentChartScale([]),{maximum:4,ticks:[4,3,2,1,0]});
  assert.deepEqual(incidentChartScale([{date:'2026-10-18',count:4}]),{maximum:8,ticks:[8,6,4,2,0]});
});

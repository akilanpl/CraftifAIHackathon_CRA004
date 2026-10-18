import test from 'node:test';
import assert from 'node:assert/strict';
import {nearestMetadataFrame, validMetadataTimeline} from '../src/replaySync.ts';

const frames = [0, 16_683_333, 33_366_667, 66_733_333, 83_416_667].map((pts_ns, index) => ({pts_ns, index}));
const verified = {toleranceNs: 8_350_000, ptsOffsetNs: 0};

test('matches exact actual PTS and returns original metadata without interpolation', () => {
  assert.equal(nearestMetadataFrame(frames, .033366667, verified), frames[2]);
  assert.equal(nearestMetadataFrame(frames, 0, verified), frames[0]);
  assert.equal(nearestMetadataFrame(frames, .032, verified), frames[2]);
});
test('missing metadata and clip boundaries remain honestly unmatched', () => {
  assert.equal(nearestMetadataFrame(frames, .05005, verified), null);
  assert.equal(nearestMetadataFrame(frames, .1, verified), null);
  const startsLate = frames.slice(2);
  assert.equal(nearestMetadataFrame(startsLate, 0, verified), null);
});
test('strict tolerance includes boundary, rejects beyond it and uses earlier midpoint tie', () => {
  const pair = [{pts_ns: 0}, {pts_ns: 20_000_000}];
  assert.equal(nearestMetadataFrame(pair, .01, {toleranceNs:10_000_000,ptsOffsetNs:0}), pair[0]);
  assert.equal(nearestMetadataFrame(pair, .01, {toleranceNs:9_999_999,ptsOffsetNs:0}), null);
  assert.equal(nearestMetadataFrame([{pts_ns:0}], .00835, verified)?.pts_ns, 0);
  assert.equal(nearestMetadataFrame([{pts_ns:0}], .008351, verified), null);
});
test('pause repeats same frame and backward/forward seeks do not retain stale selection', () => {
  const times = [.066733333, .066733333, .016683333, .083416667, .05005, 0];
  assert.deepEqual(times.map(time => nearestMetadataFrame(frames,time,verified)?.index ?? null),[3,3,1,4,null,0]);
});
test('playback rate does not affect mapping of sampled media time', () => {
  const wallElapsed = .016683333;
  // A 2x player advances twice as far in media time; matching has no wall clock.
  assert.equal(nearestMetadataFrame(frames, wallElapsed * 1, verified), frames[1]);
  assert.equal(nearestMetadataFrame(frames, wallElapsed * 2, verified), frames[2]);
  assert.equal(nearestMetadataFrame(frames, wallElapsed * 4, verified), frames[3]);
  assert.equal(nearestMetadataFrame(frames, wallElapsed * 3, verified), null);
});
test('requires an explicitly verified offset, never guesses it from first metadata', () => {
  const shifted = [{pts_ns: 33_366_667}, {pts_ns: 50_050_000}];
  assert.equal(nearestMetadataFrame(shifted,0,{...verified,ptsOffsetNs:null}),null);
  assert.equal(nearestMetadataFrame(shifted,0,verified),null);
  assert.equal(nearestMetadataFrame(shifted,0,{...verified,ptsOffsetNs:33_366_667}),shifted[0]);
  assert.equal(nearestMetadataFrame([{pts_ns:0}],.01,{...verified,ptsOffsetNs:-10_000_000})?.pts_ns,0);
});
test('rejects invalid controls and empty or malformed timelines', () => {
  assert.equal(nearestMetadataFrame([],0,verified),null);
  for (const time of [NaN,Infinity,-1]) assert.equal(nearestMetadataFrame(frames,time,verified),null);
  for (const toleranceNs of [NaN,Infinity,-1]) assert.equal(nearestMetadataFrame(frames,0,{...verified,toleranceNs}),null);
  assert.equal(nearestMetadataFrame(frames,0,{...verified,ptsOffsetNs:NaN}),null);
  assert.equal(nearestMetadataFrame([{pts_ns:NaN}],0,verified),null);
  assert.equal(nearestMetadataFrame([{pts_ns:-1}],0,verified),null);
  assert.equal(validMetadataTimeline(frames),true);
  assert.equal(validMetadataTimeline([{pts_ns:2},{pts_ns:1}]),false);
  assert.equal(validMetadataTimeline([{pts_ns:1},{pts_ns:1}]),false);
  assert.equal(validMetadataTimeline([{pts_ns:Infinity}]),false);
});

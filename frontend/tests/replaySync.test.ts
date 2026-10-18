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

test('verified recorded-source PTS offset preserves first-frame alignment through seek and resume', () => {
 const actualOffset=33_366_700;
 const actualFrames=[{pts_ns:33_366_700,index:0},{pts_ns:50_050_050,index:1},{pts_ns:66_733_400,index:2}];
 const options={ptsOffsetNs:actualOffset,toleranceNs:8_350_000};
 assert.equal(nearestMetadataFrame(actualFrames,0,options),actualFrames[0]);
 const secondTime=(actualFrames[1].pts_ns-actualOffset)/1e9;
 assert.equal(nearestMetadataFrame(actualFrames,secondTime,options),actualFrames[1]);
 assert.equal(nearestMetadataFrame(actualFrames,secondTime,options),actualFrames[1]);
 assert.equal(nearestMetadataFrame(actualFrames,0,options),actualFrames[0]);
 assert.equal(nearestMetadataFrame(actualFrames,.5,options),null);
 assert.equal(nearestMetadataFrame(actualFrames,secondTime,{...options,ptsOffsetNs:null}),null);
});

test('variable-frame-duration metadata and long gaps never stretch a detection to fill missing video time',()=>{
 const variable=[{pts_ns:0,track:'first'},{pts_ns:20_000_000,track:'second'},{pts_ns:100_000_000,track:'third'},{pts_ns:130_000_000,track:'last'}];
 const options={ptsOffsetNs:0,toleranceNs:8_350_000};
 assert.equal(validMetadataTimeline(variable),true);
 assert.equal(nearestMetadataFrame(variable,.02,options),variable[1]);
 assert.equal(nearestMetadataFrame(variable,.055,options),null);
 assert.equal(nearestMetadataFrame(variable,.1,options),variable[2]);
 assert.equal(nearestMetadataFrame(variable,.13,options),variable[3]);
 assert.equal(nearestMetadataFrame(variable,.16,options),null);
 // Pause and repeated seek operate on the same real observation, not synthetic copies.
 assert.equal(nearestMetadataFrame(variable,.1,options),nearestMetadataFrame(variable,.1,options));
});

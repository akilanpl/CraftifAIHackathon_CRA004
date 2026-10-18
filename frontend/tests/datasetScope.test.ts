import test from 'node:test';
import assert from 'node:assert/strict';
import {DatasetScopeGate} from '../src/datasetScope.ts';

test('a WebSocket factory transition invalidates an in-flight historical REST snapshot',()=>{
 const scope=new DatasetScopeGate();scope.observe('replay:street:old-hash');const streetRequest=scope.snapshot();
 assert.equal(scope.observe('replay:factory:PENDING'),true);
 assert.equal(scope.isCurrent(streetRequest),false);
 assert.equal(scope.isCurrent(scope.snapshot()),true);
});
test('same-profile telemetry preserves valid snapshots but READY and source-hash changes invalidate them',()=>{
 const scope=new DatasetScopeGate();scope.observe('factory:PENDING');const pending=scope.snapshot();
 assert.equal(scope.observe('factory:PENDING'),false);assert.equal(scope.isCurrent(pending),true);
 scope.observe('factory:READY:new-hash');assert.equal(scope.isCurrent(pending),false);
 const ready=scope.snapshot();scope.observe('factory:READY:replacement-hash');assert.equal(scope.isCurrent(ready),false);
});
test('a profile switch away and back never revalidates a stale response',()=>{
 const scope=new DatasetScopeGate();scope.observe('street');const old=scope.snapshot();
 scope.observe('factory');scope.observe('street');assert.equal(scope.isCurrent(old),false);
});

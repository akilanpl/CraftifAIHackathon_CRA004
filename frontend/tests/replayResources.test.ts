import test from 'node:test';
import assert from 'node:assert/strict';
import {PromiseResourceCache,LatestRequestGate,matchingReplayIdentity} from '../src/replayResources.ts';
function deferred<T>(){let resolve!:(value:T)=>void;let reject!:(error:Error)=>void;const promise=new Promise<T>((yes,no)=>{resolve=yes;reject=no});return {promise,resolve,reject}}

test('late failed timeline cannot evict newer successful retry cached under the same profile',async()=>{
 const cache=new PromiseResourceCache<string>();const old=deferred<string>();
 const oldRequest=cache.get('factory',()=>old.promise);const observed=oldRequest.catch(()=>null);
 cache.invalidate('factory');const fresh=cache.get('factory',async()=>'factory-correct');
 assert.equal(await fresh,'factory-correct');old.reject(new Error('old network failure'));await observed;
 assert.equal(cache.get('factory',async()=>'incorrect replacement'),fresh);
});
test('retry, profile change and disposal reject late fetch completions',()=>{
 const gate=new LatestRequestGate();const old=gate.begin();const retry=gate.begin();
 assert.equal(gate.isCurrent(old),false);assert.equal(gate.isCurrent(retry),true);
 gate.invalidate();assert.equal(gate.isCurrent(retry),false);
 const factory=gate.begin();assert.equal(gate.isCurrent(factory),true);
});
test('profile and source hashes never accept old street metadata as factory evidence',()=>{
 const expected={id:'factory',metadata_sha256:'factory-metadata',video_sha256:'factory-video'};
 assert.equal(matchingReplayIdentity(expected,{id:'historical-street'}),false);
 assert.equal(matchingReplayIdentity(expected,{...expected,metadata_sha256:'old'}),false);
 assert.equal(matchingReplayIdentity(expected,{...expected,video_sha256:'old'}),false);
 assert.equal(matchingReplayIdentity(expected,undefined),false);
 assert.equal(matchingReplayIdentity(expected,{...expected}),true);
 assert.equal(matchingReplayIdentity(undefined,undefined),true);
});
test('failed resource is retryable and separate profile caches remain isolated',async()=>{
 const cache=new PromiseResourceCache<string>();
 await assert.rejects(cache.get('factory',async()=>{throw new Error('not ready')}));
 assert.equal(await cache.get('factory',async()=>'factory'),'factory');
 assert.equal(await cache.get('street',async()=>'street'),'street');
 assert.equal(await cache.get('factory',async()=>'wrong'),'factory');
});

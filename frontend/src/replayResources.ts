/** A late failed request must never remove a newer cached timeline. */
export class PromiseResourceCache<T> {
 private entries=new Map<string,Promise<T>>();
 get(key:string,load:()=>Promise<T>):Promise<T>{
  const current=this.entries.get(key);if(current)return current;
  let pending:Promise<T>;
  pending=Promise.resolve().then(load).catch(error=>{if(this.entries.get(key)===pending)this.entries.delete(key);throw error});
  this.entries.set(key,pending);return pending;
 }
 invalidate(key:string){this.entries.delete(key)}
}
/** Each retry, profile transition, and disposal invalidates earlier callbacks. */
export class LatestRequestGate {
 private generation=0;
 begin(){return ++this.generation}
 isCurrent(token:number){return token===this.generation}
 invalidate(){this.generation++}
}
export type ReplayIdentity={id:string;metadata_sha256?:string|null;video_sha256?:string|null};
/** Explicit profile identities cannot silently accept a response from another scene. */
export function matchingReplayIdentity(expected:ReplayIdentity|undefined,actual:ReplayIdentity|undefined):boolean {
 if(!expected)return true;
 if(!actual||actual.id!==expected.id)return false;
 return (!expected.metadata_sha256||expected.metadata_sha256===actual.metadata_sha256)&&(!expected.video_sha256||expected.video_sha256===actual.video_sha256);
}

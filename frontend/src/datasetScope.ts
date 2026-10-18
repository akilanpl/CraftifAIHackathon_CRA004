/** Dataset snapshots may be committed only while their observed profile is current. */
export class DatasetScopeGate {
 private key:string|null=null;
 private epoch=0;
 observe(key:string):boolean {
  if(key===this.key)return false;
  this.key=key;this.epoch++;return true;
 }
 snapshot(){return {key:this.key,epoch:this.epoch}}
 isCurrent(token:{key:string|null;epoch:number}){return token.key===this.key&&token.epoch===this.epoch}
}

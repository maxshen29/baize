const fs=require('fs');
const path=require('path');
const html=fs.readFileSync(path.join(__dirname,'index.html'),'utf8');
const lines=html.split(/\r?\n/);

function slice(a,b){return lines.slice(a-1,b).join('\n');}

const src=[
  slice(590,661),
  slice(1305,1522)
].join('\n');

const sandbox={};
const fn=new Function(src+'\n;return {CDR_SCHEMES,NUM_ANCHORS,vDomainAnchors,scoreAntibodyChain,detectAntibody,approxNumbering,buildAbChain,aa1};');
const api=fn();

const pdb=fs.readFileSync(process.argv[2],'utf8').split(/\r?\n/);
const chains=new Map();
let inModel=true;
for(const L of pdb){
  if(L.startsWith('ENDMDL')) break;
  if(!L.startsWith('ATOM')) continue;
  const alt=L[16];
  if(alt!==' '&&alt!=='A') continue;
  const name=L.substr(12,4).trim();
  if(name!=='CA'&&name!=='N') continue;
  const chain=L[21];
  const resn=L.substr(17,3).trim();
  const resi=(L.substr(22,4).trim()+L[26].trim());
  if(!chains.has(chain)) chains.set(chain,[]);
  const arr=chains.get(chain);
  if(arr.length&&arr[arr.length-1].resi===resi&&arr[arr.length-1].resn===resn) continue;
  arr.push({chain,resn,resi,key:chain+':'+resi});
}
console.log('chains:',[...chains.keys()].map(c=>c+'('+chains.get(c).length+')').join(' '));

for(const [cid,residues] of chains){
  const a=api.vDomainAnchors(residues);
  console.log('\n=== chain '+cid+' n='+residues.length+' ===');
  if(!a){console.log('  no V-domain anchors -> not an antibody V chain'); continue;}
  console.log('  kind='+a.kind+' c1='+a.c1+' w2='+a.w2+' c2='+a.c2+' f4='+a.f4+' vEnd='+a.vEnd);
  const s=api.scoreAntibodyChain(residues);
  console.log('  score='+s.score);
  const vseq=residues.slice(0,a.vEnd+1).map(r=>api.aa1(r.resn)).join('');
  console.log('  V seq ('+vseq.length+'): '+vseq);
  console.log('  anchor resi: c1='+residues[a.c1].resi+' w2='+residues[a.w2].resi+' c2='+residues[a.c2].resi+' f4='+residues[a.f4].resi);
  for(const sch of Object.keys(api.CDR_SCHEMES)){
    const ch=api.buildAbChain({chains:[{id:cid,residues}]},cid,a,sch,{});
    const d=ch.spans;
    const f=(k)=>{const [x,y]=d[k];return '['+api.aa1(residues[x].resn)+(x)+'-'+api.aa1(residues[y].resn)+(y)+'] pdb:'+residues[x].resi+'-'+residues[y].resi;};
    console.log('  '+sch.padEnd(9)+' CDR1 '+f('1').padEnd(34)+' CDR2 '+f('2').padEnd(34)+' CDR3 '+f('3'));
    console.log('             seq: '+ch.cdrSeq.CDR1+' | '+ch.cdrSeq.CDR2+' | '+ch.cdrSeq.CDR3);
  }
}

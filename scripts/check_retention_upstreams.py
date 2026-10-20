"""Read-only upstream audit. No unlicensed source or checkpoints redistributed."""
import urllib.request,json,pathlib,hashlib,time
ROOT=pathlib.Path(__file__).resolve().parents[1]
repos=['gmrandazzo/PyLSS','gurevichlab/grip','josiehong/TIMPANI','compomics/DeepLC','boecker-lab/2-step']
records=[]
def get(url):return urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'EluSim-scientific-audit'}),timeout=30).read()
for repo in repos:
 try:
  meta=json.loads(get('https://api.github.com/repos/'+repo));commit=json.loads(get('https://api.github.com/repos/'+repo+'/commits?per_page=1'))[0]
  tree=json.loads(get('https://api.github.com/repos/'+repo+'/git/trees/'+commit['sha']+'?recursive=1'))['tree']
  files=[r['path'] for r in tree if r['type']=='blob'];licenses=[p for p in files if p.rsplit('/',1)[-1].lower().startswith(('license','copying'))]
  code=[p for p in files if p.endswith('.py') and any(w in p.lower() for w in ['predict','infer','model','engine'])][:3]
  inspected=[]
  for path in code:
   content=get('https://raw.githubusercontent.com/'+repo+'/'+commit['sha']+'/'+path)
   inspected.append({'path':path,'sha256':hashlib.sha256(content).hexdigest(),'bytes':len(content),'output_markers':[w for w in ['logkw','logk','retention','rtpred','smiles','gradient'] if w in content.decode(errors='replace').lower()]})
  records.append({'repo':repo,'commit':commit['sha'],'license':meta.get('license'),'license_files':licenses,'reviewed_core_files':inspected,'weight_files':[p for p in files if p.endswith(('.ckpt','.pt','.pth','.h5','.pkl'))][:30]})
  print(repo,commit['sha'],meta.get('license',{}),flush=True)
 except Exception as e:records.append({'repo':repo,'error':str(e)});print(repo,e,flush=True)
(ROOT/'docs/v2-evidence/retention-upstream-recheck.json').write_text(json.dumps(records,indent=2),encoding='utf8')

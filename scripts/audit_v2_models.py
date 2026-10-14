import json,pathlib,urllib.request,concurrent.futures
ROOT=pathlib.Path(__file__).resolve().parents[1]; OUT=ROOT/'docs/v2-evidence';OUT.mkdir(parents=True,exist_ok=True)
def get(url):
 req=urllib.request.Request(url,headers={'User-Agent':'EluSim-scientific-audit'})
 return urllib.request.urlopen(req,timeout=40).read()
def audit(repo):
 info=json.loads(get('https://api.github.com/repos/'+repo));commit=json.loads(get('https://api.github.com/repos/'+repo+'/commits/'+info['default_branch']));sha=commit['sha'];tree=json.loads(get('https://api.github.com/repos/'+repo+'/git/trees/'+sha+'?recursive=1'))
 data={'repo':repo,'commit':sha,'license':info.get('license'),'tree':tree.get('tree',[]),'files':{}}
 candidates=[x for x in data['tree'] if x['type']=='blob' and x.get('size',0)<80000 and (x['path'].lower() in ['readme.md','license','license.txt','requirements.txt','environment.yml','env.yaml','pyproject.toml','grip_inference.py','predict.py','get_model_files.sh','uvvisml/data/readme.md'] or ('predict' in x['path'] and x['path'].endswith('.py')))]
 for x in candidates[:12]:
  try:data['files'][x['path']]=get('https://raw.githubusercontent.com/'+repo+'/'+sha+'/'+x['path']).decode()
  except Exception as exc:data['files'][x['path']]=str(exc)
 (OUT/(repo.replace('/','__')+'.json')).write_text(json.dumps(data,indent=2),encoding='utf8')
 return {'repo':repo,'sha':sha,'license':info.get('license'),'files':list(data['files']),'models':[x for x in data['tree'] if x['path'].endswith(('.ckpt','.pt','.pth','.pkl','.csv','.tsv'))][:12]}
if __name__=='__main__':
 repos=['gurevichlab/grip','gmrandazzo/PyLSS','compomics/DeepLC','josiehong/TIMPANI','boecker-lab/2-step','learningmatter-mit/uvvisml','PNNL-CompBio/ML_UVvisModels','michaelwitting/RepoRT']
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
  for r in pool.map(audit,repos):print(json.dumps(r),flush=True)

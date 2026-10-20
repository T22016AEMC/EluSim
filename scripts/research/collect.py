"""Read-only GitHub audit; snapshots live outside the application in TEMP."""
import concurrent.futures, json, os, pathlib, urllib.request, zipfile, io
ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / 'docs/research-evidence'
CACHE = pathlib.Path(os.environ['TEMP']) / 'lc-gradient-research-20261013'
REPOS = ['gmrandazzo/PyLSS','gurevichlab/grip','sartorius-research/STLC','jonkeeley/openiex','boecker-lab/2-step','josiehong/TIMPANI','DLUT-datas/MDL-TL','statisticalbiotechnology/NonlinearGradientsUI','cadet/CADET-Core','cadet/CADET-Process','HopkinsLaboratory/Graphormer-RT','CompOmics/DeepLC','michaelwitting/RepoRT','yufree/mzrtsim','jraysajulga/High-Performance-Liquid-Chromatography-Research-Programs']
def get(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'LC-Gradient-Studio-research'}),timeout=90) as r: return r.read()
def audit(repo):
    slug=repo.replace('/','__'); result={'repo':repo}
    try:
        meta=json.loads(get('https://api.github.com/repos/'+repo)); result['metadata']=meta
        commit=json.loads(get('https://api.github.com/repos/'+repo+'/commits/'+meta['default_branch'])); result['commit']=commit
        sha=commit['sha']; tree=json.loads(get('https://api.github.com/repos/'+repo+'/git/trees/'+sha+'?recursive=1')); result['tree']=tree
        result['issues']=json.loads(get('https://api.github.com/repos/'+repo+'/issues?state=all&per_page=20'))
        target=CACHE/slug; target.mkdir(parents=True,exist_ok=True)
        # Download text source only; do not fetch or execute serialized model files.
        paths=[x['path'] for x in tree.get('tree',[]) if x['type']=='blob' and x.get('size',0)<250000 and (x['path'].endswith(('.py','.java','.toml','.yaml','.yml','.txt','.md','.R','.cpp','.hpp','.h','.json','.sh')) or 'LICENSE' in x['path'].upper() or 'COPYING' in x['path'].upper())]
        def file(path):
            try:
                data=get('https://raw.githubusercontent.com/'+repo+'/'+sha+'/'+urllib.parse.quote(path)); dest=target/path; dest.parent.mkdir(parents=True,exist_ok=True); dest.write_bytes(data)
            except Exception as e: return {'path':path,'error':str(e)}
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool: result['file_errors']=[e for e in pool.map(file,paths) if e]
        result['snapshot']=str(target); result['downloaded_text_paths']=paths
    except Exception as e: result['error']=str(e)
    OUT.mkdir(parents=True,exist_ok=True); (OUT/(slug+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return {'repo':repo,'sha':result.get('commit',{}).get('sha'),'error':result.get('error'),'files':len(result.get('downloaded_text_paths',[]))}
if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for result in pool.map(audit,REPOS): print(json.dumps(result),flush=True)

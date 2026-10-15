"""Record bounded license metadata and issue samples, without claiming a full SBOM."""
import pathlib,os,json,hashlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[2]; E=ROOT/'docs/research-evidence'; CACHE=pathlib.Path(os.environ['TEMP'])/'lc-gradient-research-20261013'
rows=[]
for directory in sorted(CACHE.iterdir()):
 if not directory.is_dir() or directory.name.startswith('venv'):continue
 found=[]
 for p in directory.iterdir():
  if p.is_file() and ('license' in p.name.lower() or 'copying' in p.name.lower() or p.name=='DESCRIPTION'):
   raw=p.read_bytes(); content=raw.decode('utf8',errors='replace')
   found.append({'path':p.name,'sha256':hashlib.sha256(raw).hexdigest(),'evidence_excerpt':content[:900]})
 rows.append({'repository_snapshot':directory.name,'root_license_files':found,'note':'Empty list means no root license found; vendor licenses are not blanket project licenses.'})
(E/'license-file-evidence.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf8')
code="import json,importlib.metadata as m; print(json.dumps([{'name':d.metadata['Name'],'version':d.version,'license_expression':d.metadata.get('License-Expression'),'license_metadata':(d.metadata.get('License') or '')[:1500],'license_classifiers':[s for s in d.metadata.get_all('Classifier',[]) if s.startswith('License ::')]} for d in m.distributions()]))"
for name in ['pylss','stlc','openiex']:
 py=CACHE/('venv-'+name)/'Scripts/python.exe'
 result=subprocess.run([str(py),'-c',code],capture_output=True,text=True,encoding='utf8',timeout=90)
 if result.returncode: raise RuntimeError(result.stderr)
 (E/(name+'-dependency-license-metadata.json')).write_text(json.dumps(json.loads(result.stdout),indent=2,ensure_ascii=False),encoding='utf8')
print('license artifacts recorded')

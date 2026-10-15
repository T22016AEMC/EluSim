import pathlib, subprocess, urllib.request, zipfile, io, json, os, sys
git=r'C:/Users/T22016/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/git/cmd/git.exe'
root=pathlib.Path(__file__).resolve().parents[2]
for repo in (sys.argv[1:] or ['fau-advanced-separations/CADET-Process','jraysajulga/High-Performance-Liquid-Chromatography-Research-Programs']):
 result={'repo':repo}
 try:
  ref=subprocess.check_output([git,'ls-remote','https://github.com/'+repo+'.git','HEAD'],text=True,timeout=60).split()[0]
  result['sha']=ref
  try:
   with urllib.request.urlopen('https://github.com/'+repo+'/commit/'+ref+'.patch',timeout=30) as p:
    header=p.read(16000).decode('utf8',errors='replace')
   result['commit_patch_header']=header.split('\n---\n')[0][:4000]
  except Exception as e: result['patch_error']=str(e)
  data=urllib.request.urlopen('https://codeload.github.com/'+repo+'/zip/'+ref,timeout=120).read()
  dest=pathlib.Path(os.environ['TEMP'])/'lc-gradient-research-20261013'/repo.replace('/','__'); dest.mkdir(parents=True,exist_ok=True)
  paths=[]
  with zipfile.ZipFile(io.BytesIO(data)) as z:
   for item in z.infolist():
    path=pathlib.PurePosixPath(item.filename); rel=pathlib.Path(*path.parts[1:])
    if item.is_dir() or '..' in rel.parts: continue
    if item.file_size<2000000 and (rel.suffix in ['.py','.java','.md','.toml','.txt','.yml','.yaml','.cpp','.h','.R','.ipynb','.sh'] or 'LICENSE' in rel.name.upper() or rel.name in ['DESCRIPTION','Dockerfile']):
     f=dest/rel; f.parent.mkdir(parents=True,exist_ok=True); f.write_bytes(z.read(item)); paths.append(str(rel))
  result['snapshot']=str(dest); result['paths']=paths
  print(repo,ref,'files',len(paths),flush=True)
 except Exception as e: result['error']=str(e); print(repo,repr(e),flush=True)
 (root/'docs/research-evidence'/('extra-'+repo.replace('/','__')+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')

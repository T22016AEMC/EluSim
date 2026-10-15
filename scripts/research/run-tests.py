import pathlib,sys,os,subprocess,json
ROOT=pathlib.Path(__file__).resolve().parents[2]; CACHE=pathlib.Path(os.environ['TEMP'])/'lc-gradient-research-20261013'
OUT=ROOT/'docs/research-evidence'
for name in (sys.argv[1:] or ['pylss','stlc','openiex']):
 py=CACHE/('venv-'+name)/'Scripts/python.exe'
 cmd=[str(py),'-X','utf8',str(ROOT/'scripts/research/probe.py'),name]
 with (OUT/(name+'-probe.log')).open('w',encoding='utf8') as log:
  log.write('COMMAND '+subprocess.list2cmdline(cmd)+'\n'); log.flush()
  try: result=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=180); print(name,result.returncode,flush=True)
  except subprocess.TimeoutExpired: print(name,'TIMEOUT',flush=True); log.write('TIMEOUT 180s\n')
 if name=='pylss':
  cmd=[str(py),'-m','pytest',str(CACHE/'gmrandazzo__PyLSS/tests'),'-q']
  with (OUT/'pylss-upstream-tests.log').open('w',encoding='utf8') as log:
   log.write('COMMAND '+subprocess.list2cmdline(cmd)+'\n'); log.flush()
   p=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=180); print('pylss upstream',p.returncode,flush=True)

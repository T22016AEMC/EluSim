"""Create three independent TEMP virtualenvs. No global/app dependencies modified."""
import pathlib, os, subprocess, sys, venv, json
ROOT=pathlib.Path(__file__).resolve().parents[2]
CACHE=pathlib.Path(os.environ['TEMP'])/'lc-gradient-research-20261013'
cases={'pylss':('gmrandazzo__PyLSS',['numpy','scipy','matplotlib','PyYAML','pytest']), 'stlc':('sartorius-research__STLC',['numpy','scipy','matplotlib']), 'openiex':('jonkeeley__openiex',['numpy','scipy','matplotlib','pandas','tqdm','ipywidgets'])}
logs=ROOT/'docs/research-evidence'; logs.mkdir(parents=True,exist_ok=True)
for name,(slug,deps) in cases.items():
 env=CACHE/('venv-'+name); venv.EnvBuilder(with_pip=True).create(env); py=env/'Scripts/python.exe'
 commands=[[str(py),'-m','pip','install',*deps],[str(py),'-m','pip','install','--no-deps','--no-build-isolation','-e',str(CACHE/slug)]]
 commands.insert(1,[str(py),'-m','pip','install','setuptools','wheel'])
 with (logs/(name+'-install.log')).open('w',encoding='utf8') as log:
  for cmd in commands:
   log.write('COMMAND '+subprocess.list2cmdline(cmd)+'\n'); log.flush()
   p=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=300)
   log.write('EXIT '+str(p.returncode)+'\n'); log.flush()
   if p.returncode: break
 print(name,'install exit',p.returncode,flush=True)

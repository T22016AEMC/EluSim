"""Resume timed-out isolated install, preserving the original attempt log."""
import pathlib, subprocess, os
root=pathlib.Path(__file__).resolve().parents[2]
cache=pathlib.Path(os.environ['TEMP'])/'lc-gradient-research-20261013'
py=cache/'venv-openiex/Scripts/python.exe'
commands=[[str(py),'-m','pip','install','numpy','scipy','matplotlib','pandas','tqdm','ipywidgets'],[str(py),'-m','pip','install','setuptools','wheel'],[str(py),'-m','pip','install','--no-deps','--no-build-isolation','-e',str(cache/'jonkeeley__openiex')]]
with (root/'docs/research-evidence/openiex-install-resume.log').open('w',encoding='utf8') as log:
 for cmd in commands:
  log.write('COMMAND '+subprocess.list2cmdline(cmd)+'\n'); log.flush()
  try: p=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=600)
  except subprocess.TimeoutExpired: log.write('TIMEOUT 600s\n'); raise
  log.write('EXIT '+str(p.returncode)+'\n'); log.flush()
  if p.returncode: raise SystemExit(p.returncode)
print('OpenIEX resume completed',flush=True)

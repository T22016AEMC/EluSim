"""Repository inventory; filename deliberately avoids stdlib inspect.py."""
import json, pathlib, os, re
root=pathlib.Path(__file__).resolve().parents[2]
for p in sorted((root/'docs/research-evidence').glob('*.json')):
 d=json.loads(p.read_text(encoding='utf8'))
 if 'repo' not in d: continue
 m=d.get('metadata',{}); c=d.get('commit',{})
 print('\nREPO',d['repo'],'SHA',c.get('sha'),'DATE',c.get('commit',{}).get('committer',{}).get('date'),'LICENSE',m.get('license'),'ISSUES',m.get('open_issues_count'),'ARCHIVED',m.get('archived'),'ERROR',d.get('error'))
 print('TEST/CI', [x['path'] for x in d.get('tree',{}).get('tree',[]) if x['type']=='blob' and (x['path'].startswith(('test/','tests/','.github/workflows/')))])
 print('WEIGHTS',[{'path':x['path'],'size':x.get('size')} for x in d.get('tree',{}).get('tree',[]) if x['path'].endswith(('.pt','.ckpt','.h5','.onnx','.pkl'))][:30])
 if 'snapshot' in d:
  for name in ['LICENSE','LICENSE.md','COPYING','pyproject.toml','requirements.txt','setup.py','environment.yml']:
   f=pathlib.Path(d['snapshot'])/name
   if f.exists():
    txt=f.read_text(encoding='utf8',errors='replace'); print('FILE',name,txt[:900] if name.startswith(('LICENSE','COPYING')) else txt[:6000])

import pathlib,json,importlib.metadata as meta,os
root=pathlib.Path.cwd()
rows=[]
for d in meta.distributions():
 files=[]
 for p in d.files or []:
  if any(x in str(p).lower() for x in ['license','copying','notice']):files.append(str(p))
 rows.append({'name':d.metadata['Name'],'version':d.version,'expression':d.metadata.get('License-Expression'),'metadata_license':(d.metadata.get('License') or '')[:2500],'classifiers':[x for x in d.metadata.get_all('Classifier',[]) if x.startswith('License ::')],'license_files':files[:40]})
(root/'docs/elusim-v1-python-license-inventory.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False),encoding='utf8')
front=[]
store=root/'frontend/node_modules/.pnpm'
for folder in store.iterdir():
 node=folder/'node_modules'
 if not node.exists():continue
 for p in node.glob('*/package.json'):
  try:d=json.loads(p.read_text(encoding='utf8'));front.append({k:d.get(k) for k in ['name','version','license']})
  except (ValueError,OSError):pass
 for p in node.glob('@*/*/package.json'):
  try:d=json.loads(p.read_text(encoding='utf8'));front.append({k:d.get(k) for k in ['name','version','license']})
  except (ValueError,OSError):pass
(root/'docs/elusim-v1-js-license-inventory.json').write_text(json.dumps(front,indent=2),encoding='utf8')
print('License inventory:',len(rows),'Python and',len(front),'JS records; metadata not legal advice')

"""Collect full installed dependency license notices for the deployed source offer."""
import pathlib,importlib.metadata as meta,hashlib
root=pathlib.Path.cwd();parts=['EluSim_V1 dependency notices. Project license remains AGPL-3.0-or-later.\n']
seen=set()
for d in meta.distributions():
 for entry in d.files or []:
  if not any(word in str(entry).lower() for word in ['license','copying','notice']):continue
  p=pathlib.Path(d.locate_file(entry))
  if not p.is_file() or p.stat().st_size>500000:continue
  raw=p.read_bytes()
  if b'\x00' in raw:continue
  key=hashlib.sha256(raw).hexdigest()
  if key in seen:continue
  seen.add(key);parts.append('\n===== '+d.metadata['Name']+' '+d.version+' / '+str(entry)+' =====\n'+raw.decode('utf8',errors='replace'))
store=root/'frontend/node_modules/.pnpm'
for name in ['react','react-dom','scheduler','echarts','zrender','tslib']:
 matches=sorted(store.glob(name+'@*'))
 if not matches:raise FileNotFoundError('Runtime dependency '+name)
 folder=matches[0]/'node_modules'/name
 for p in folder.iterdir():
  if p.is_file() and any(word in p.name.lower() for word in ['license','copying','notice']):parts.append('\n===== '+matches[0].name+' / '+p.name+' =====\n'+p.read_text(encoding='utf8',errors='replace'))
target=root/'third_party/RUNTIME_LICENSES.txt';target.write_text('\n'.join(parts),encoding='utf8')
print('Runtime dependency notices saved:',target.stat().st_size,'bytes')

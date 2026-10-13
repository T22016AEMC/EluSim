"""Copy unmodified, pinned AGPL reference subset; no NLSS path is included."""
import pathlib,os,json,hashlib
root=pathlib.Path(__file__).resolve().parents[1]
source=pathlib.Path(os.environ['TEMP'])/'lc-gradient-research-20261013/gmrandazzo__PyLSS'
target=root/'third_party/pylss';target.mkdir(parents=True,exist_ok=True)
records=[]
for filename in ['ssengine.py','optimizer.py','miscalgoritms.py']:
 raw=(source/'src/pylss'/filename).read_bytes();(target/filename).write_bytes(raw)
 records.append({'file':filename,'sha256':hashlib.sha256(raw).hexdigest(),'modified':False})
(target/'__init__.py').write_text('# AGPL-3.0-or-later: pinned reference package\n',encoding='utf8')
license_data=(source/'LICENSE').read_bytes();(target/'LICENSE').write_bytes(license_data);(root/'LICENSE').write_bytes(license_data)
(target/'PROVENANCE.json').write_text(json.dumps({'repository':'https://github.com/gmrandazzo/PyLSS','commit':'d2cda850fa0b0881fc3cf1cd68c4d93b59dac04f','files':records,'role':'Optional reference test, production engine independently derived'},indent=2),encoding='utf8')
print('Pinned PyLSS reference and full AGPL license copied')

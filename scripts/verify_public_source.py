"""Verify the public corresponding-source archive without extracting files."""
import io,json,tarfile,urllib.request,pathlib,datetime
url='https://elusim-v1.onrender.com'
with urllib.request.urlopen(url+'/api/source',timeout=90) as response:
 data=response.read(32*1024*1024+1)
assert len(data)<=32*1024*1024
with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as archive:
 names=archive.getnames()
 for required in ['LICENSE','NOTICE.md','data/retention/LICENSE.md','data/retention/curves.json','backend/models/lss-parameters.json.gz','backend/elusim/retention_registry.py']:
  assert 'EluSim_V2/'+required in names,required
 assert not any(pathlib.PurePosixPath(n).name=='.env' or '/.git/' in n or '/.venv/' in n for n in names)
report={'url':url+'/api/source','timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS','files':len(names),'bytes':len(data),'required_licensed_data_and_model_present':True,'no_env_git_or_venv_paths':True}
(pathlib.Path(__file__).resolve().parents[1]/'artifacts/public-source-check.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))

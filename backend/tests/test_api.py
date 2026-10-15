import pytest
from fastapi.testclient import TestClient
from elusim.main import app,_rates
from test_engine import method
client=TestClient(app)

@pytest.fixture(autouse=True)
def clean_rates():_rates.clear()

def test_health_descriptors_and_invalid_structure():
 assert client.get('/api/health').json()['status']=='ok'
 r=client.post('/api/compounds/describe',json={'name':'caffeine'})
 assert r.status_code==200 and r.json()['formula']=='C8H10N4O2'
 assert r.json()['retention_parameters'] is None
 assert client.post('/api/compounds/describe',json={'smiles':'not a structure'}).status_code==422

def test_csv_and_mol_roundtrip_import():
 r=client.post('/api/compounds/import',files={'file':('mixture.csv','name,smiles,logkw,s\nEthanol,CCO,2,4\n','text/csv')})
 assert r.status_code==200 and r.json()['compounds'][0]['s']==4
 from rdkit import Chem
 mol=Chem.MolToMolBlock(Chem.MolFromSmiles('CCO'))
 r=client.post('/api/compounds/import',files={'file':('ethanol.mol',mol,'text/plain')})
 assert r.json()['compounds'][0]['smiles']=='CCO'

def test_real_compute_process_simulation_api():
 r=client.post('/api/simulate',json=method().model_dump())
 assert r.status_code==200 and len(r.json()['order'])==3

def test_no_unknown_fields_or_external_url_fetch():
 assert client.post('/api/compounds/describe',json={'url':'http://169.254.169.254/'}).status_code==422
 assert client.post('/api/simulate',json={}).status_code==422

def test_payload_and_rate_limits():
 assert client.post('/api/compounds/describe',content=b'x'*1048577).status_code==413
 _rates.clear()
 for _ in range(30):assert client.post('/api/compounds/describe',json={'smiles':'CCO'}).status_code==200
 assert client.post('/api/compounds/describe',json={'smiles':'CCO'}).status_code==429

def test_import_count_and_supported_modes():
 assert client.post('/api/compounds/import',files={'file':('x.csv','name\n'+'Synthetic\n'*21,'text/csv')}).status_code==422
 assert client.get('/api/library').json()['modes']['HILIC']['quantitative'] is False

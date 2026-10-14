import json,pathlib
import numpy as np
import pytest
from fastapi.testclient import TestClient
from elusim.main import app,_rates
from elusim.features import molecular_features
from elusim.prediction import load_model,infer,predict_retention,report_method,prepare_structure
from elusim.uv import predict_uv,import_spectrum
from elusim.retention_data import normalize_observation,fit_retention_curve
from elusim.engine import simulate
from test_engine import method
client=TestClient(app)
@pytest.fixture(autouse=True)
def clean_rates():_rates.clear()
def eligible_heldout(mid):
 model=load_model(mid)
 for smiles in model['metadata']['test_smiles']:
  r=infer(mid,smiles)
  if r['prediction'] is not None:return smiles,r
 raise AssertionError('No in-domain independently heldout molecule')
def exact_method():
 m=method();template=report_method();m.column=m.column.model_copy(update=template['column']);m.mobile=m.mobile.model_copy(update=template['mobile']);m.gradient=[type(m.gradient[0])(**n) for n in template['gradient']];return m
def test_real_descriptors_and_independent_scaffold_holdout():
 a,_=molecular_features('CCO');b,_=molecular_features('c1ccccc1');assert a['descriptors']!=b['descriptors'] and a['fingerprint']!=b['fingerprint']
 for mid in ['report0259-rt','pnnl-uv-shape']:
  m=load_model(mid)['metadata'];assert not set(m['test_smiles'])&set(m['train_smiles']);assert m['beats_mean_baseline'];s,r=eligible_heldout(mid);assert not r['applicability']['seen_in_training'];assert r['status']=='Experimental model prediction'
def test_direct_rt_only_and_exact_method_constraints():
 s,_=eligible_heldout('report0259-rt');m=exact_method();r=predict_retention(s,m);assert r['rt_min']>0 and r['logkw'] is None and r['s'] is None
 for key,value in [('stationary_phase','Other C18'),('length_mm',150),('temperature_c',25)]:
  other=m.model_copy(deep=True);setattr(other.column,key,value);assert predict_retention(s,other)['rt_min'] is None
 m.gradient[1].time_min+=.1;assert predict_retention(s,m)['rt_min'] is None
def test_out_of_domain_and_manual_fallback():
 assert infer('report0259-rt','[Na+]')['prediction'] is None
 m=method();m.workflow='structure';assert not simulate(m)['order'];m.workflow='known';assert len(simulate(m)['order'])==3
def test_lss_adapter_output_is_really_used_and_gradient_changes(monkeypatch):
 import elusim.prediction as p
 m=method();m.workflow='structure';m.compounds=m.compounds[:1];m.compounds[0].kind='small_molecule';m.compounds[0].smiles='CCO'
 scope={'mode':'RP','stationary_phase':m.column.stationary_phase,'mobile_a':m.mobile.a,'mobile_b':m.mobile.b,'buffer':m.mobile.buffer,'ph':m.mobile.ph,'temperature_c':m.column.temperature_c}
 class FixtureRoot:
  def __truediv__(self,other):return self
  def exists(self):return True
 monkeypatch.setattr(p,'ROOT',FixtureRoot());monkeypatch.setattr(p,'load_model',lambda mid:{'metadata':{'scope':scope}});monkeypatch.setattr(p,'infer',lambda mid,s:{'prediction':[2.,4.],'status':'Experimental model prediction','model':{'source':'Synthetic adapter fixture only; not deployed empirical model'}})
 r=simulate(m);assert r['peaks'][0]['rt_min'] is not None and r['structure_predictions']
 before=r['peaks'][0]['rt_min'];m.gradient[1].time_min=15;assert simulate(m)['peaks'][0]['rt_min']>before
 m.mobile.b='MeOH';assert not simulate(m)['order']
def curve_row(phi,logk):
 return {'smiles':'CCO','mode':'RP','stationary_phase':'test','mobile_a':'Water','mobile_b':'ACN','buffer':'None','ph':7,'temperature_c':25,'source':'Synthetic fixture, not empirical evidence','license':'test','phi':phi,'logk':logk}
def test_identifiability_units_and_scope():
 r=curve_row(.2,1.2);r.pop('logk');r['rt_min']=3;assert normalize_observation(r)['identifiability'].startswith('Single')
 with pytest.raises(ValueError):fit_retention_curve([r])
 fit=fit_retention_curve([curve_row(.2,1.2),curve_row(.5,0)]);assert fit['logkw']==pytest.approx(2) and fit['s']==pytest.approx(4)
 with pytest.raises(ValueError):fit_retention_curve([curve_row(.2,1),curve_row(.2,2)])
 with pytest.raises(ValueError):normalize_observation({**curve_row(.5,0),'rt_min':2,'t0_min':1,'elution':'gradient'})
def test_full_uv_shape_units_and_no_fake_padding():
 s,_=eligible_heldout('pnnl-uv-shape');r=predict_uv(s);assert r['spectrum'];x=r['spectrum']['wavelength_nm'];y=r['spectrum']['intensity'];assert len(x)==len(y)==181 and x[0]==220 and x[-1]==400 and np.ptp(y)>0
 assert not r['molar_absorptivity_available'];assert r['lambda_max_nm'] in x
 assert predict_uv(s,solvent='MeOH')['spectrum'] is None
 assert predict_uv(s,start_nm=500,end_nm=800)['spectrum'] is None
 assert predict_uv('CCCC')['spectrum'] is None
 assert predict_uv('CC=O')['chromophores']!=predict_uv('c1ccccc1')['chromophores']
def test_two_molecules_do_not_share_fixed_spectrum():
 eligible=[s for s in load_model('pnnl-uv-shape')['metadata']['test_smiles'] if infer('pnnl-uv-shape',s)['prediction'] is not None][:2]
 a=predict_uv(eligible[0]);b=predict_uv(eligible[1]);assert not np.allclose(a['spectrum']['intensity'],b['spectrum']['intensity'])
def test_experimental_import_keeps_original_and_units():
 raw='wavelength_nm,intensity\n220,-0.01\n250,0.5\n400,0.1\n';r=import_spectrum(raw,'Test','absorbance');assert r['original_csv']==raw and r['intensity'][0]==-.01 and not r['transformations']
 with pytest.raises(ValueError):import_spectrum('wavelength_nm,intensity\n250,1\n220,2','x','absorbance')
def test_v2_api_and_bounds():
 assert client.get('/api/models').status_code==200
 s,_=eligible_heldout('pnnl-uv-shape');r=client.post('/api/uv/predict',json={'smiles':s});assert r.status_code==200 and r.json()['spectrum']
 assert client.post('/api/uv/predict',json={'smiles':s,'start_nm':800,'end_nm':200}).status_code==422
 assert client.post('/api/uv/predict',json={'smiles':s,'url':'http://169.254.169.254'}).status_code==422
 assert client.post('/api/retention/predict',json={'smiles':eligible_heldout('report0259-rt')[0],'method':exact_method().model_dump()}).json()['rt_min']>0

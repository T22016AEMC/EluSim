"""Real measured curve fixtures are distinct from synthetic numerical checks."""
import math,csv,io,json,pathlib
import numpy as np
import pytest
from test_engine import method
from elusim.schemas import Compound,Node,Optimize
from elusim.engine import simulate,optimize
from elusim.conditions import method_scope
from elusim.retention_registry import measured_curves,predict_curve,resolve_compounds
from elusim.prediction import load_model,infer
from elusim.mixture import signal_amounts
from elusim.chemistry import import_file

def scoped_method():
 m=method();scope=measured_curves()[0]['scope'];m.column.stationary_phase=scope['stationary_phase'];m.column.temperature_c=35;m.column.particle_um=3.5
 m.mobile.a=scope['mobile_a'];m.mobile.b=scope['mobile_b'];m.mobile.buffer=scope['buffer'];m.mobile.ph=None;m.mobile.ph_control='formulation'
 m.gradient=[Node(time_min=0,b_percent=20,temperature_c=35),Node(time_min=10,b_percent=50,temperature_c=35),Node(time_min=60,b_percent=50,temperature_c=35)]
 m.compounds=[Compound(id=str(i),name='Experimental curve '+str(i),smiles=r['smiles'],mixture_parts=p) for i,(r,p) in enumerate(zip(measured_curves()[:3],[5,3,2]))]
 return m

def test_three_real_smiles_curves_and_auto_parameter_resolution():
 m=scoped_method();prepared,records=resolve_compounds(m)
 assert len({json.dumps(r['features']['descriptors'],sort_keys=True) for r in records})==3
 assert all(c.logkw is not None and c.s is not None and c.source=='literature_derived' for c in prepared.compounds)
 assert all(len(r['observations'])>=4 and len(r['curve']['k'])==31 for r in records)
 for c,r in zip(prepared.compounds,records):assert c.id==r['compound_id'] and c.retention_provenance['canonical_smiles']==r['features']['canonical_smiles']
 assert len(simulate(prepared)['order'])==3

def test_unseen_qsrr_parameters_really_feed_solver():
 m=scoped_method();model=load_model('lss-parameters');assert not set(model['metadata']['train_smiles'])&set(model['metadata']['test_smiles'])
 sm=next(s for s in model['metadata']['test_smiles'] if infer('lss-parameters',s)['prediction'] is not None)
 r=predict_curve(sm,m,use_literature=False);assert r['logkw'] is not None and not r['applicability']['seen_in_training']
 c=Compound(id='unseen',name='Heldout QSRR',smiles=sm,logkw=r['logkw'],s=r['s'],scope=r['scope'],source=r['status'],parameter_origin='prediction',retention_provenance={'canonical_smiles':r['features']['canonical_smiles'],'phi_range':r['phi_range'],'particle_um':3.5})
 m.compounds=[c];first=simulate(m)['peaks'][0]['rt_min'];m.gradient[1].time_min=20;second=simulate(m)['peaks'][0]['rt_min']
 assert first is not None and second is not None and second>first

def test_conditions_and_range_cannot_silently_transfer_parameters():
 m,_=resolve_compounds(scoped_method())
 for field,value in [('stationary_phase','Generic C18'),('temperature_c',25),('particle_um',1.7)]:
  other=m.model_copy(deep=True);setattr(other.column,field,value)
  if field=='temperature_c':other.gradient=[n.model_copy(update={'temperature_c':value}) for n in other.gradient]
  assert not simulate(other)['order']
 other=m.model_copy(deep=True);other.mobile.b='MeOH';assert not simulate(other)['order']
 other=m.model_copy(deep=True);other.mobile.ph=3;other.mobile.ph_control='fixed';assert not simulate(other)['order']
 other=m.model_copy(deep=True);other.gradient[0].b_percent=5;assert not simulate(other)['order']
 other=m.model_copy(deep=True);other.compounds[0].smiles='CCO';assert simulate(other)['peaks'][0]['rt_min'] is None

def test_parts_area_not_height_and_rt_invariance():
 m,_=resolve_compounds(scoped_method());m.points=2000;m.gradient[-1].time_min=20;r=simulate(m)
 assert [p['mixture_fraction'] for p in r['peaks']]==pytest.approx([.5,.3,.2])
 assert [p['peak_area'] for p in r['peaks']]==pytest.approx([.5,.3,.2])
 for p in r['peaks']:assert p['peak_height']*math.sqrt(2*math.pi)*p['sigma_min']==pytest.approx(p['peak_area'])
 for trace,p in zip(r['traces'],r['peaks']):assert np.trapezoid(trace['y'],r['time_min'])==pytest.approx(p['peak_area'],rel=.01)
 m.compounds[0].mixture_parts=10;q=simulate(m)
 assert [p['rt_min'] for p in q['peaks']]==pytest.approx([p['rt_min'] for p in r['peaks']])
 assert q['peaks'][0]['peak_area']>r['peaks'][0]['peak_area']
 m.compounds=m.compounds[::-1];assert signal_amounts(m)['0']['mixture_fraction']==pytest.approx(10/15)

def test_concentration_amount_units_and_invalid_composition():
 m=scoped_method();m.mixture_basis='concentration'
 for c in m.compounds:c.concentration=2;c.concentration_unit='mM'
 m.mobile.injection_ul=5;s=signal_amounts(m);assert s['0']['injected_amount']==10 and s['0']['amount_unit']=='nmol'
 for c in m.compounds:c.concentration_unit='mg/mL'
 assert signal_amounts(m)['0']['amount_unit']=='µg'
 m.compounds[0].concentration_unit='mM'
 with pytest.raises(ValueError):signal_amounts(m)
 m.mixture_basis='parts'
 for c in m.compounds:c.mixture_parts=0
 with pytest.raises(ValueError):simulate(m)
 with pytest.raises(ValueError):Compound(id='a',name='x',mixture_parts=-1)

def test_manual_protection_and_explicit_replacement():
 m=scoped_method();m.compounds[0].logkw=2;m.compounds[0].s=4
 p,records=resolve_compounds(m);assert p.compounds[0].logkw==2 and records[0]['status']=='Manual parameters preserved'
 p,records=resolve_compounds(m,overwrite_manual=True);assert p.compounds[0].logkw!=2 and p.compounds[0].source=='literature_derived'

def test_optimizer_uses_same_curve_and_rejects_ineligible_base():
 m,_=resolve_compounds(scoped_method());r=optimize(Optimize(simulation=m,durations_min=[8,12],starts_percent=[20],ends_percent=[50],hold_min=10))
 assert r['evaluated']==2
 for candidate in r['candidates']:
  expected=simulate(m.model_copy(update={'gradient':[Node(**n) for n in candidate['gradient']],'points':300}))
  assert [p['rt_min'] for p in expected['peaks']]==pytest.approx([p['rt_min'] for p in candidate['result']['peaks']])
 m.mobile.b='MeOH'
 with pytest.raises(ValueError):optimize(Optimize(simulation=m))

def test_composition_import_ids_and_validation():
 raw='name,smiles,mixture_parts,concentration,concentration_unit,response_factor\nCaffeine,Cn1c(=O)c2c(ncn2C)n(C)c1=O,5,2,mM,1\n'
 a=import_file(raw,'x.csv');b=import_file(raw,'x.csv');assert a[0]['mixture_parts']==5 and a[0]['id']!=b[0]['id']
 with pytest.raises(ValueError):import_file(raw.replace(',5,2,mM,1',',-5,2,mM,1'),'x.csv')

def test_real_data_license_split_and_no_false_rt_accuracy():
 root=pathlib.Path(__file__).resolve().parents[2];errors=json.loads((root/'docs/v2-evidence/scoped-retention-errors.json').read_text())
 model=load_model('lss-parameters')['metadata'];assert model['license']=='CC-BY-NC-SA-3.0-US' and model['beats_mean_baseline']
 assert errors['heldout_observations']>=3 and errors['logk_rmse']>0 and errors['rt_mae_min'] is None
 assert predict_curve('[Na+]',scoped_method(),use_literature=False)['logkw'] is None

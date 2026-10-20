"""Legacy source compatibility and real numerical/dataflow regressions."""
import pytest
from fastapi.testclient import TestClient
from elusim.main import app,_rates
from elusim.schemas import Simulation,Compound,Optimize
from elusim.engine import simulate,optimize
from elusim.retention_registry import predict_curve,resolve_compounds,curve_conditions
from test_engine import method
from test_retention_integration import scoped_method
client=TestClient(app)
@pytest.fixture(autouse=True)
def clean_rates():_rates.clear()

@pytest.mark.parametrize('legacy,code',[('基於模型','model_based'),('Model-based','model_based'),('Measured','measured'),('Literature-derived','literature_derived'),('old unknown label','unknown_legacy'),('model_based','model_based')])
def test_source_codes_keep_parameters_and_true_solver_results(legacy,code):
 data=method().model_dump();data['compounds'][0]['source']=legacy
 parsed=Simulation.model_validate(data)
 assert parsed.compounds[0].source==code
 assert parsed.compounds[0].logkw==2 and parsed.compounds[0].s==4
 if legacy!=code:assert parsed.compounds[0].source_legacy==legacy
 result=simulate(parsed)
 assert len(result['traces'])==3 and len(set(p['rt_min'] for p in result['peaks']))==3
 assert result['peaks'][0]['source']=='model_based'
 assert result['peaks'][0]['parameter_tier']=='M'


def test_legacy_api_not_just_200_and_field_error_is_specific():
 data=method().model_dump()
 for c,value in zip(data['compounds'],['基於模型','Model-based','unrecognized legacy source']):c['source']=value
 r=client.post('/api/simulate',json=data)
 assert r.status_code==200,r.text
 result=r.json();assert len(result['order'])==3 and all(max(t['y'])>0 for t in result['traces'])
 assert result['input']['compounds'][2]['source']=='unknown_legacy'
 data['compounds'][1]['s']=-2;r=client.post('/api/simulate',json=data)
 assert r.status_code==422 and r.json()['detail'][0]['loc']==['body','compounds',1,'s']


def test_real_lookup_model_conditions_and_detailed_warnings():
    """Lookup and optimization retain values while reporting source differences."""
    request = scoped_method()
    actual = curve_conditions()
    assert actual['scope'] == predict_curve(request.compounds[0].smiles, request)['model']['scope']
    response = client.post('/api/retention/resolve', json={'method': request.model_dump()})
    assert response.status_code == 200
    compounds = response.json()['compounds']
    assert all(compound['source'] == 'literature_derived' for compound in compounds)
    request.compounds = [Compound.model_validate(compound) for compound in compounds]
    assert len(simulate(request)['traces']) == 3
    request.mobile.b = 'MeOH'
    request.column.particle_um = 1.7
    warned = predict_curve(request.compounds[0].smiles, request)
    assert warned['logkw'] is not None
    assert any('mobile_b' in item for item in warned['condition_mismatches'])
    assert any('particle_um' in item for item in warned['condition_mismatches'])
    result = optimize(Optimize(simulation=request, durations_min=[8], starts_percent=[20], ends_percent=[50]))
    assert result['evaluated'] == 1
    assert result['candidates'][0]['result']['peaks'][0]['warning']


def test_failed_estimation_keeps_parameters_and_reports_structure_warning():
    """An invalid new structure cannot overwrite existing numerical parameters."""
    request = scoped_method()
    request.compounds[0].logkw = 2
    request.compounds[0].s = 4
    request.compounds[0].smiles = 'not-a-smiles'
    kept, records = resolve_compounds(request, overwrite_manual=True)
    assert kept.compounds[0].logkw == 2 and kept.compounds[0].s == 4
    assert records[0]['status'] == 'Insufficient data'
    resolved, _ = resolve_compounds(scoped_method())
    resolved.compounds[0].smiles = 'not-a-smiles'
    result = simulate(resolved)
    assert result['peaks'][0]['simulation_status'] == 'eluted'
    assert len(result['traces']) == 3
    assert 'SMILES cannot be parsed' in result['peaks'][0]['warning']


def test_nonelution_is_distinct_from_invalid_parameters_and_import_ids():
 m=method();m.compounds[0].logkw=12;m.compounds[0].s=0;m.compounds[1].s=None
 result=simulate(m)
 assert result['peaks'][0]['simulation_status']=='non_eluted'
 assert result['peaks'][1]['simulation_status']=='ineligible'
 assert result['peaks'][2]['simulation_status']=='eluted'
 from rdkit import Chem
 from elusim.chemistry import import_file
 raw=Chem.MolToMolBlock(Chem.MolFromSmiles('CCO'))
 assert import_file(raw,'a.mol')[0]['id']!=import_file(raw,'a.mol')[0]['id']


def test_structure_workflow_returns_effective_parameters_used_by_solver():
 m=scoped_method();m.workflow='structure'
 result=simulate(m)
 assert all(c['logkw'] is None for c in result['input']['compounds'])
 assert all(c['logkw'] is not None and c['source']=='literature_derived' for c in result['resolved_compounds'])
 replay=m.model_copy(update={'workflow':'known','compounds':[Compound.model_validate(c) for c in result['resolved_compounds']]})
 assert [p['rt_min'] for p in simulate(replay)['peaks']]==pytest.approx([p['rt_min'] for p in result['peaks']])


def test_non_database_structure_uses_actual_qsrr_and_enters_solver():
 from elusim.retention_registry import measured_curves
 from elusim.features import molecular_features
 smiles='CC(=O)Nc1ccc(OCCC)cc1'
 canonical=molecular_features(smiles)[0]['canonical_smiles']
 assert canonical not in {r['smiles'] for r in measured_curves()}
 m=scoped_method();m.compounds=[Compound(id='nonlookup',name='Non-database structure',smiles=smiles)];m.workflow='structure'
 prepared,records=resolve_compounds(m)
 assert prepared.compounds[0].source=='experimental_model_prediction'
 assert not records[0]['applicability']['seen_in_training'] and records[0]['applicability']['accepted']
 assert 'observations' not in records[0] and 'QSRR' in records[0]['parameter_source']
 result=simulate(m);assert result['peaks'][0]['rt_min'] is not None and max(result['traces'][0]['y'])>0

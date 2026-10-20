import math
import numpy as np
import pytest
from elusim.schemas import Simulation, Compound, Node, Optimize, Calibration
from elusim.engine import simulate,retention,volume,Program,optimize,calibrate

def method(**kwargs):
 data={'compounds':[Compound(id='a',name='Synthetic A',logkw=2,s=4),Compound(id='b',name='Synthetic B',logkw=2.5,s=4.5),Compound(id='c',name='Synthetic C',logkw=3,s=5)],'gradient':[Node(time_min=0,b_percent=5),Node(time_min=10,b_percent=95),Node(time_min=20,b_percent=95)]}
 data.update(kwargs);return Simulation(**data)

def test_isocratic_analytic_and_zero_slope():
 m=method(gradient=[Node(time_min=0,b_percent=30),Node(time_min=240,b_percent=30)])
 for c in m.compounds:
  analytic=volume(m.column)/.3*(1+10**(c.logkw-c.s*.3))
  assert retention(m,c)==pytest.approx(analytic,rel=1e-7)

def test_gradient_flow_length_sensitivity_and_early_limit():
 m=method();r=simulate(m)
 assert len(r['traces'])==3 and len(r['order'])==3 and r['min_rs']>0
 slow=m.model_copy(update={'gradient':[Node(time_min=0,b_percent=5),Node(time_min=20,b_percent=95),Node(time_min=30,b_percent=95)]})
 long=m.model_copy(update={'column':m.column.model_copy(update={'length_mm':150})})
 fast=m.model_copy(update={'gradient':[n.model_copy(update={'flow_ml_min':.6}) for n in m.gradient]})
 for c in m.compounds:
  baseline=retention(m,c)
  assert retention(slow,c)>baseline
  assert retention(long,c)>baseline
  assert retention(fast,c)<baseline

def test_dwell_transport_and_nonretained_marker():
 m=method();m.mobile.dwell_ml=1
 p=Program(m);vm=volume(m.column)
 assert p.local_phi(1,0,vm,1)==.05
 assert p.local_phi(5,.5,vm,1)<p.local_phi(5,0,vm,1)
 c=Compound(id='marker',name='Marker',logkw=-3,s=0)
 assert retention(m,c)==pytest.approx(vm/.3*1.001,rel=1e-6)

def test_piecewise_split_invariance_and_convergence():
 m=method();c=m.compounds[1]
 split=m.model_copy(update={'gradient':[m.gradient[0],Node(time_min=5,b_percent=50),*m.gradient[1:]]})
 assert retention(m,c)==pytest.approx(retention(split,c),rel=1e-6)
 a=retention(m,c,rtol=1e-6,max_step=.2);b=retention(m,c,rtol=1e-9,max_step=.025)
 assert abs(a-b)<2e-5

def test_variable_flow_volume_inverse_and_step_program():
 m=method(gradient=[Node(time_min=0,b_percent=5,flow_ml_min=.2,interpolation='step'),Node(time_min=5,b_percent=90,flow_ml_min=.4),Node(time_min=20,b_percent=90,flow_ml_min=.4)])
 p=Program(m)
 for t in np.linspace(0,20,30):assert p.time_at_volume(p.pumped(t))==pytest.approx(t,abs=1e-10)
 assert p.composition(4)==.05 and p.composition(5)==.9
 assert retention(m,m.compounds[0]) is not None

def test_noneluted_insufficient_and_unsupported():
 m=method();m.compounds[0].logkw=12;m.compounds[0].s=0;m.compounds[1].s=None
 r=simulate(m)
 assert r['peaks'][0]['rt_min'] is None and not r['peaks'][0]['eluted']
 assert r['peaks'][1]['source']=='insufficient_data'
 for mode in ['NP','HILIC','IEX','SEC']:
  r=simulate(m.model_copy(update={'mode':mode}))
  assert not r['traces'] and all(p['source']=='unsupported' for p in r['peaks'])

def test_gaussian_width_and_resolution_identity():
 r=simulate(method());a,b=r['peaks'][:2]
 assert a['fwhm_min']/a['sigma_min']==pytest.approx(2*math.sqrt(2*math.log(2)))
 assert r['pairs'][0]['rs']==pytest.approx(2*(b['rt_min']-a['rt_min'])/(4*a['sigma_min']+4*b['sigma_min']))

def test_missing_efficiency_keeps_rt_without_drawing_peaks():
    """Manual parameters stay usable in either workflow, with no N-based signal."""
    request = method()
    request.column.plates = None
    for workflow in ['known', 'structure']:
        result = simulate(request.model_copy(update={'workflow': workflow}))
        assert len(result['order']) == 3
        assert not result['traces'] and result['min_rs'] is None


def test_parameter_scope_difference_warns_without_blocking():
    """Supplied numerical parameters remain usable with an explicit difference."""
    from elusim.schemas import Scope

    request = method()
    request.compounds[0].scope = Scope(mobile_b='MeOH')
    peak = simulate(request)['peaks'][0]
    assert peak['rt_min'] is not None
    assert 'mobile_b' in peak['warning']


def test_optimization_changes_real_migration_and_respects_budget():
 req=Optimize(simulation=method(),durations_min=[8,12],starts_percent=[5],ends_percent=[95])
 out=optimize(req)
 assert out['evaluated']==2 and len(out['candidates'])==2
 assert out['candidates'][0]['result']['peaks'][0]['rt_min']!=out['candidates'][1]['result']['peaks'][0]['rt_min']
 with pytest.raises(ValueError):Optimize(simulation=method(),durations_min=list(range(1,9)),starts_percent=[5,15],ends_percent=[80,95])

def test_synthetic_calibration_identifiability_and_recovery():
 one=method();two=method(gradient=[Node(time_min=0,b_percent=5),Node(time_min=20,b_percent=95),Node(time_min=40,b_percent=95)])
 truth=one.compounds[1];observations=[{'method':m,'rt_min':retention(m,truth)} for m in [one,two]]
 fit=calibrate(Calibration(compound_id='b',observations=observations))
 assert fit['logkw']==pytest.approx(2.5,abs=.005) and fit['s']==pytest.approx(4.5,abs=.01)
 assert fit['statistical_prediction_error'] is None
 with pytest.raises(ValueError):Calibration(compound_id='b',observations=observations[:1])
 with pytest.raises(ValueError):calibrate(Calibration(compound_id='b',observations=[observations[0]]*2))

def test_invalid_units_and_temperature_boundary():
 with pytest.raises(ValueError):method(gradient=[Node(time_min=1,b_percent=5),Node(time_min=1,b_percent=100)])
 with pytest.raises(ValueError):Node(time_min=0,b_percent=101)
 with pytest.raises(ValueError):method(gradient=[Node(time_min=0,b_percent=5),Node(time_min=10,b_percent=90,temperature_c=40)])

import sys,pathlib
import pytest
from test_engine import method
from elusim.engine import retention,volume
from elusim.schemas import Compound
from elusim.jobs import compute
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2].parent))

def test_pinned_pylss_linear_reference_high_retention_limit():
 from third_party.pylss.ssengine import SSGenerator
 m=method();c=Compound(id='ref',name='Synthetic reference',logkw=4,s=8)
 vm=volume(m.column);t0=vm/.3;td=m.mobile.dwell_ml/.3
 ref=SSGenerator(100,2.1,.68,t0,m.mobile.dwell_ml,.3)
 expected=ref.rtpred(c.logkw,c.s,10,.05,.95,t0,td)
 # Upstream neglects migration before the delayed gradient; asymptotic comparison
 # only, not equivalence for all compounds / holds / isocratic methods.
 actual=retention(m,c)
 assert actual<10 and actual==pytest.approx(expected,rel=.002)

def test_disposable_job_timeout_stops_work_and_releases_capacity():
 with pytest.raises(TimeoutError):compute('simulation',method().model_dump(),timeout=.0001)
 assert len(compute('simulation',method().model_dump())['order'])==3

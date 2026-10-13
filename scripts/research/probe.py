"""Calls unmodified upstream APIs with synthetic parameters, not accuracy validation."""
import sys, pathlib, json, os, traceback, importlib.metadata, time
import numpy as np
ROOT=pathlib.Path(__file__).resolve().parents[2]; OUT=ROOT/'docs/research-evidence'
name=sys.argv[1]; data={'project':name,'synthetic':True,'python':sys.version,'packages':{p.metadata['Name']:p.version for p in importlib.metadata.distributions()}}
os.environ['MPLBACKEND']='Agg'
def peaks(t, traces):
 rows=[]
 for y in traces:
  idx=int(np.argmax(y)); ids=np.flatnonzero(y>=float(y[idx])/2)
  fwhm=float(t[ids[-1]]-t[ids[0]]) if len(ids)>1 else None
  rows.append({'rt':float(t[idx]),'height':float(y[idx]),'fwhm':fwhm,'boundary_peak':idx in (0,len(t)-1),'min':float(y.min())})
 return rows
def apparent_rs(rows):
 ordered=sorted(rows,key=lambda p:p['rt'])
 return [1.18*(b['rt']-a['rt'])/(a['fwhm']+b['fwhm']) if a['fwhm'] and b['fwhm'] else None for a,b in zip(ordered,ordered[1:])]
try:
 if name=='pylss':
  from pylss.ssengine import SSGenerator
  from pylss.gradientutils import get_lss_peak_width,get_lss_gradient_critical_rs
  from pylss.plotengine import BuildChromatogram
  params=[[2.0,4.0],[2.5,4.5],[3.0,5.0]]; cases=[]
  for L,tg,start in [(100,10,.05),(100,20,.05),(100,10,.15),(150,10,.05)]:
   g=SSGenerator(L,2.1,.68,None,.1,.3)
   rt=[g.rtpred(a,b,tg,start,.95,g.t0,g.td) for a,b in params]
   widths=[get_lss_peak_width(L/10,1.7,a,b,start,.95,tg,.3,g.v0,.1,None) for a,b in params]
   rs=get_lss_gradient_critical_rs(L/10,1.7,start,.95,tg,.3,g.v0,.1,params)
   chrom=BuildChromatogram([[r,1,w/(4/np.sqrt(2))] for r,w in zip(rt,widths)],30,.01)
   cases.append({'L_mm':L,'tg_min':tg,'phi_start':start,'t0_min':g.t0,'rt_min':rt,'width_base_min':widths,'critical_rs':rs,'chrom_shape':np.asarray(chrom).shape})
  data['cases']=cases
  assert all(np.isfinite(c['rt_min']).all() and len(set(c['rt_min']))==3 for c in cases)
  assert all(not np.allclose(cases[0]['rt_min'],c['rt_min']) for c in cases[1:])
  data['zero_gradient_result']=g.rtpred(2.,4.,10,.05,.05,g.t0,g.td)
  try:
   import pylss.nlssengine
   data['nlss_import']='PASS'
  except Exception as e: data['nlss_import']={'status':'FAILED','error':repr(e)}
  data['status']='PASS_HEADLESS_API'; data['caveat']='Requires supplied logKw/S, no structure prediction; GUI dependencies omitted.'
 elif name=='stlc':
  from stlc import lkm
  import matplotlib.pyplot as plt
  cases=[]
  for L,dt in [(1.0,.05),(1.5,.05),(1.0,.025)]:
   pars=[lkm.ModelParameters(u=.29,ep=.4,D=.002,c0=1,k=10,a=a,b=0,ip=lambda t:float(t<1)) for a in [.2,.5,.8]]
   model=lkm.LumpedKineticModel(3,5,L,pars); y=lkm.solve(model,30,dt); t=np.arange(y.shape[1])*dt
   traces=[y[i*model.q_end+model.c_end-1] for i in range(3)]; rows=peaks(t,traces)
   np.savez_compressed(OUT/('stlc-'+str(L)+'-'+str(dt)+'.npz'),t=t,outlet=traces)
   assert np.isfinite(y).all() and all(not row['boundary_peak'] for row in rows)
   cases.append({'L':L,'dt':dt,'shape':y.shape,'finite':bool(np.isfinite(y).all()),'peaks':rows,'apparent_rs_fwhm':apparent_rs(rows)})
   if L==1 and dt==.05:
    for trace in traces: plt.plot(t,trace)
    plt.xlabel('Time (upstream model units)'); plt.ylabel('Outlet concentration'); plt.savefig(OUT/'stlc-peaks.png'); plt.close()
  data['cases']=cases; data['status']='PASS_SYNTHETIC_TRANSPORT'; data['caveat']='No native solvent-gradient-dependent binding API in lkm; not SMILES prediction.'
 elif name=='openiex':
  from openiex.species import Ion,Protein
  from openiex.config import SystemConfig
  from openiex.system import ExchangeSystem
  from openiex.method import Method,validate_method
  from openiex.state import initialize_state
  from openiex.solver import run_simulation,method_duration
  import matplotlib.pyplot as plt
  cases=[]
  for L,grad in [(.01,3),(.01,6),(.015,3)]:
   cfg=SystemConfig(L,.002,.05,.4,.3,Nz=8)
   salt={'salt':Ion('salt',D=1e-7,unit='M')}
   proteins={f'P{i}':Protein(f'P{i}',D=1e-7,sigma=1,nu=1+i*.3,unit='M') for i in range(3)}
   system=ExchangeSystem(salt,proteins,{},cfg)
   for i,p in enumerate(proteins): system.set_equilibrium(p,'salt',float(i-1),-1.)
   try:
    rebuilt=ExchangeSystem.from_dict(system.to_dict())
    data['serialization_roundtrip_equal']=rebuilt.to_math_dict()==system.to_math_dict()
   except Exception as e: data['serialization_roundtrip_error']=repr(e)
   data['reverse_lnK_example']={'forward':system.ln_K_eq[('P0','salt')],'reverse':system.ln_K_eq[('salt','P0')],'expected_reverse':-system.ln_K_eq[('P0','salt')]}
   base={'salt':.02,**{p:0. for p in proteins}}; high={**base,'salt':.5}; load={**base,**{p:1e-5 for p in proteins}}
   def block(a,b,start,end,cv): return {'buffer_A':a,'buffer_B':b,'start_B':start,'end_B':end,'duration_CV':cv,'flow_rate_mL_min':.1}
   method=Method({'base':base,'high':high,'load':load},[block('load','load',0,0,.2),block('base','base',0,0,1),block('base','high',0,1,grad),block('high','high',0,0,3)])
   validate_method(method,system); y0=initialize_state({'salt':{'C':.02,'Q':.05}},system)
   # Same sampling interval across methods: avoid mistaking changed sample bins
   # for genuine gradient effects on early (pre-gradient) peaks.
   final=method_duration(method,system); t=np.unique(np.r_[np.arange(0,final,.5),final])
   result=run_simulation(y0,t,method,system,rtol=1e-5,atol=1e-9)
   traces=[result.y[(i+1)*cfg.Nz+cfg.Nz-1] for i in range(3)]
   rows=peaks(result.t,traces)
   cases.append({'L_m':L,'gradient_CV':grad,'gradient_start_s':final*1.2/(grad+4.2),'sampling_interval_s':.5,'t_final_s':final,'returned_final_s':float(result.t[-1]),'finite':bool(np.isfinite(result.y).all()),'peaks':rows,'apparent_rs_fwhm':apparent_rs(rows)})
   np.savez_compressed(OUT/('openiex-'+str(L)+'-'+str(grad)+'.npz'),t=result.t,outlet=traces)
   if L==.01 and grad==3:
    for trace in traces: plt.plot(result.t,trace)
    plt.xlabel('Time (s)'); plt.ylabel('Outlet concentration (M)'); plt.savefig(OUT/'openiex-peaks.png'); plt.close()
  data['cases']=cases; data['status']='EXECUTED_REVIEW_REQUIRED'; data['caveat']='Synthetic protein parameters; reverse lnK bug; wrapper omits solve_ivp success flag. No structure predictor.'
except Exception as e:
 data['status']='FAILED'; data['error']=repr(e); data['traceback']=traceback.format_exc()
 print(data['traceback'],flush=True)
(OUT/(name+'-probe.json')).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in data.items() if k!='packages'},ensure_ascii=False),flush=True)

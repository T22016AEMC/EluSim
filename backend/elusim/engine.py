"""Independent LSS migration ODE, not a translation of upstream PyLSS code.
Local solvent composition follows plug-flow volume transport; no adsorption of
solvent and no compressibility. Synthetic verification is not experimental validation.
"""
import math, time
import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import least_squares
from .schemas import Simulation, Optimize, Calibration

MODEL = 'elusim-lss-migration/1.0.0'
MODES = {
 'RP': {'quantitative':True,'parameters':['logkw','s'],'description':'LSS with supplied / calibrated parameters'},
 'NP': {'quantitative':False,'parameters':['adsorption_constant','solvent_competition','water_activity'],'description':'Competitive adsorption model not validated'},
 'HILIC': {'quantitative':False,'parameters':['partition_coefficient','adsorption_constant','ionic_contribution'],'description':'Mixed retention mechanisms not validated'},
 'IEX': {'quantitative':False,'parameters':['capacity','nu','sigma','ka','kd','salt_molar'],'description':'SMA binding validation pending; OpenIEX excluded'},
 'SEC': {'quantitative':False,'parameters':['accessible_pore_volume_ml','partition_coefficient','hydrodynamic_radius_nm'],'description':'Pore accessibility / size relation not validated'},
}

def volume(column):
 return column.void_ml if column.void_ml is not None else math.pi*column.diameter_mm**2/4*column.length_mm*column.porosity/1000

class Program:
 def __init__(self, req):
  self.t=np.array([n.time_min for n in req.gradient]); self.f=np.array([n.flow_ml_min for n in req.gradient]); self.phi=np.array([n.b_percent/100 for n in req.gradient]); self.step=[n.interpolation=='step' for n in req.gradient]
  self.slopes=np.diff(self.f)/np.diff(self.t)
  self.v=np.r_[0,np.cumsum(np.diff(self.t)*(self.f[:-1]+self.f[1:])/2)]
 def interval(self,t): return min(max(int(np.searchsorted(self.t,t,side='right')-1),0),len(self.t)-2)
 def flow(self,t): return float(np.interp(t,self.t,self.f))
 def pumped(self,t):
  if t<=0:return 0.
  if t>=self.t[-1]:return float(self.v[-1]+(t-self.t[-1])*self.f[-1])
  j=self.interval(t);dt=t-self.t[j];return float(self.v[j]+self.f[j]*dt+.5*self.slopes[j]*dt*dt)
 def time_at_volume(self,v):
  if v<=0:return 0.
  if v>=self.v[-1]:return float(self.t[-1]+(v-self.v[-1])/self.f[-1])
  j=min(int(np.searchsorted(self.v,v,side='right')-1),len(self.slopes)-1);dv=v-self.v[j];a=self.slopes[j];f=self.f[j]
  dt=dv/f if abs(a)<1e-12 else 2*dv/(f+math.sqrt(max(0,f*f+2*a*dv)))
  return float(self.t[j]+dt)
 def composition(self,t):
  if t<=0:return float(self.phi[0])
  if t>=self.t[-1]:return float(self.phi[-1])
  j=self.interval(t)
  return float(self.phi[j] if self.step[j] else np.interp(t,self.t,self.phi))
 def local_phi(self,t,x,vm,dwell):
  return self.composition(self.time_at_volume(self.pumped(t)-dwell-max(0,x)*vm))

def retention(req,compound,rtol=1e-7,max_step=None):
 p=Program(req); vm=volume(req.column);end=p.t[-1]
 def rhs(t,y):
  exponent=compound.logkw-compound.s*p.local_phi(t,y[0],vm,req.mobile.dwell_ml)
  k=10.**exponent
  return [p.flow(t)/(vm*(1+k))]
 def eluted(t,y):return y[0]-1
 eluted.terminal=True;eluted.direction=1
 sol=solve_ivp(rhs,(0,end),[0.],method='DOP853',events=eluted,rtol=rtol,atol=rtol*1e-2,max_step=max_step or min(.1,end/80))
 if not sol.success: raise ValueError('Migration solver failed')
 return float(sol.t_events[0][0]) if len(sol.t_events[0]) else None

def eligibility(req,c):
 if req.mode!='RP': return 'Unsupported', f'{req.mode}: independent quantitative model not enabled'
 if req.workflow=='structure':return 'Insufficient data','目前缺少經驗證的結構預測模型'
 if c.kind in ['polymer','peptide','protein','oligomer']:return 'Unsupported','No validated LSS model for this entity kind'
 if c.logkw is None or c.s is None:return 'Insufficient data','Missing logKw / S'
 if req.workflow=='calibrated' and c.source!='Calibrated':return 'Insufficient data','No calibrated parameters for this component'
 if c.scope:
  s=c.scope
  if s.stationary_phase!=req.column.stationary_phase or s.mobile_a!=req.mobile.a or s.buffer!=req.mobile.buffer or s.mobile_b!=req.mobile.b or abs(s.ph-req.mobile.ph)>.01 or abs(s.temperature_c-req.column.temperature_c)>.01:
   return 'Insufficient data','Parameters are outside their declared stationary phase / solvent / pH / temperature scope'
 return c.source,None

def simulate(req:Simulation,deadline=None):
 from .prediction import prepare_structure
 original_input=req.model_dump();req,predictions=prepare_structure(req)
 p=Program(req); vm=volume(req.column); grid=np.linspace(0,p.t[-1],req.points);peaks=[];curves=[];warnings=[]
 for c in req.compounds:
  if deadline and time.monotonic()>deadline:raise TimeoutError('Computation budget exceeded')
  source,error=eligibility(req,c)
  row={'id':c.id,'name':c.name,'source':source,'rt_min':None,'eluted':False,'warning':error,'sigma_min':None,'fwhm_min':None,'width_base_min':None}
  if not error:
   rt=retention(req,c)
   row['rt_min']=rt;row['eluted']=rt is not None
   if rt is None:row['warning']='Non-eluted within programmed run; not assigned a fictitious Rt'
   elif req.column.plates:
    sigma=math.sqrt(rt*rt/req.column.plates+(req.mobile.injection_ul/1000/p.flow(0))**2/12+req.mobile.extra_sigma_min**2)
    row.update(sigma_min=sigma,fwhm_min=2*math.sqrt(2*math.log(2))*sigma,width_base_min=4*sigma)
    curves.append({'id':c.id,'name':c.name,'y':(c.amplitude*np.exp(-.5*((grid-rt)/sigma)**2)).tolist()})
   else:row['warning']='Efficiency missing: Rt only; peak / Rs not generated'
   if c.scope is None:warnings.append(c.name+': parameter scope undeclared; comparisons are conditional on these supplied parameters')
  peaks.append(row)
 ordered=sorted([r for r in peaks if r['eluted']],key=lambda r:r['rt_min']);pairs=[]
 for a,b in zip(ordered,ordered[1:]):
  rs=2*(b['rt_min']-a['rt_min'])/(a['width_base_min']+b['width_base_min']) if a['width_base_min'] and b['width_base_min'] else None
  pairs.append({'ids':[a['id'],b['id']],'names':[a['name'],b['name']],'rs':rs,'coelution':rs is not None and rs<1.5})
 if len(grid)>1 and any(r['sigma_min'] and (grid[1]-grid[0])>r['sigma_min']/2 for r in peaks):warnings.append('Plot grid is coarse relative to some peak widths; use exported peak metrics')
 return {'input':original_input,'structure_predictions':predictions,'model':MODEL,'mode':req.mode,'peaks':peaks,'pairs':pairs,'order':[r['id'] for r in ordered],'min_rs':min((r['rs'] for r in pairs if r['rs'] is not None),default=None),'time_min':grid.tolist(),'traces':curves,'gradient':{'program_b_percent':[100*p.composition(t) for t in grid],'inlet_b_percent':[100*p.local_phi(t,0,vm,req.mobile.dwell_ml) for t in grid]},'void_ml':vm,'initial_t0_min':vm/p.flow(0),'total_solvent_ml':float(p.v[-1]),'warnings':list(dict.fromkeys(warnings)),'assumptions':['Dilute local equilibrium LSS; plug-flow solvent transport; no overload','Gaussian screening width sigma = Rt/sqrt(N) plus injection and extra-column variance; no validated gradient compression','Specified pH / temperature / solvent do not independently modify LSS parameters; parameter scope must match','No externally validated prediction error or confidence interval'],'uncertainty':{'quantified':False,'reason':'No external experimental validation dataset'},'pressure':{'available':False,'reason':'Missing viscosity, permeability and instrument pressure model'}}

def optimize(req:Optimize):
 from .schemas import Node
 base=req.simulation
 if base.mode!='RP' or any(eligibility(base,c)[1] for c in base.compounds) or not base.column.plates or len(base.compounds)<2:raise ValueError('Optimization needs ≥2 eligible RP components and column efficiency')
 deadline=time.monotonic()+20; results=[]
 for duration in req.durations_min:
  for start in req.starts_percent:
   for end in req.ends_percent:
    if end<=start:continue
    nodes=[Node(time_min=0,b_percent=start,flow_ml_min=base.gradient[0].flow_ml_min,temperature_c=base.column.temperature_c),Node(time_min=duration,b_percent=end,flow_ml_min=base.gradient[0].flow_ml_min,temperature_c=base.column.temperature_c)]
    if req.hold_min:nodes.append(nodes[-1].model_copy(update={'time_min':duration+req.hold_min}))
    sim=base.model_copy(update={'gradient':nodes,'points':300});result=simulate(sim,deadline)
    all_eluted=all(x['eluted'] for x in result['peaks']);rs=result['min_rs'];solvent=result['total_solvent_ml']
    feasible=all_eluted and rs is not None and rs>=req.target_rs and (req.max_solvent_ml is None or solvent<=req.max_solvent_ml)
    results.append({'gradient':[x.model_dump() for x in nodes],'feasible':feasible,'all_eluted':all_eluted,'min_rs':rs,'duration_min':nodes[-1].time_min,'solvent_ml':solvent,'result':result,'limits':['Pressure limit not evaluated: physical properties missing','Gaussian efficiency approximation; no experimental accuracy claim']})
 results.sort(key=lambda x:(not x['feasible'],not x['all_eluted'],max(0,req.target_rs-(x['min_rs'] or 0)),x['duration_min'],x['solvent_ml']))
 return {'candidates':results[:8],'evaluated':len(results),'search':'Bounded enumerated linear-gradient grid; global optimality not claimed','recommendations':[{'mode':m,'status':'Screening only' if m!='RP' else 'Model-based','note':MODES[m]['description']} for m in MODES]}

def calibrate(req:Calibration):
 methods=[o.method for o in req.observations]
 if any(m.mode!='RP' for m in methods):raise ValueError('RP calibration only')
 signatures=[str((m.column.model_dump(),m.mobile.model_dump(),[n.model_dump() for n in m.gradient])) for m in methods]
 if len(set(signatures))<2:raise ValueError('Need at least two independent methods; duplicate Rt cannot identify two parameters')
 first=methods[0];scope=(first.column.stationary_phase,first.mobile.b,first.mobile.ph,first.column.temperature_c,first.mobile.a,first.mobile.buffer)
 if any((m.column.stationary_phase,m.mobile.b,m.mobile.ph,m.column.temperature_c,m.mobile.a,m.mobile.buffer)!=scope for m in methods):raise ValueError('Calibration methods must share stationary phase, solvents, buffer, pH and temperature')
 compounds=[]
 for m in methods:
  c=next((x for x in m.compounds if x.id==req.compound_id),None)
  if c is None or c.kind not in ['small_molecule','parameterized']:raise ValueError('Missing / unsupported calibration component')
  compounds.append(c)
 target=np.array([o.rt_min for o in req.observations]);deadline=time.monotonic()+20
 def residual(values):
  if time.monotonic()>deadline:raise TimeoutError('Calibration budget exceeded')
  return np.array([(retention(m,c.model_copy(update={'logkw':float(values[0]),'s':float(values[1])})) or m.gradient[-1].time_min*2) for m,c in zip(methods,compounds)])-target
 fit=least_squares(residual,[2.,4.],bounds=([-3,0],[12,30]),max_nfev=100,diff_step=1e-4)
 if not fit.success or np.linalg.matrix_rank(fit.jac)<2 or np.linalg.cond(fit.jac)>1e6:raise ValueError('Parameters not identifiable / optimizer not converged')
 if any(retention(m,c.model_copy(update={'logkw':float(fit.x[0]),'s':float(fit.x[1])})) is None for m,c in zip(methods,compounds)):raise ValueError('Calibration predicts non-elution')
 return {'compound_id':req.compound_id,'logkw':float(fit.x[0]),'s':float(fit.x[1]),'source':'Calibrated','scope':{'stationary_phase':scope[0],'mobile_b':scope[1],'ph':scope[2],'temperature_c':scope[3],'mobile_a':scope[4],'buffer':scope[5]},'residuals_min':fit.fun.tolist(),'rmse_fit_min':float(np.sqrt(np.mean(fit.fun**2))),'jacobian_condition':float(np.linalg.cond(fit.jac)),'statistical_prediction_error':None,'warning':'Training fit residual is not external prediction accuracy; synthetic inputs remain synthetic','model':MODEL}

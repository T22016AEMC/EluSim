"""Independent LSS migration ODE, not a translation of upstream PyLSS code.
Local solvent composition follows plug-flow volume transport; no adsorption of
solvent and no compressibility. Synthetic verification is not experimental validation.
"""
import math, time
from dataclasses import dataclass
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

@dataclass(frozen=True)
class RetentionState:
    """Outlet state at the migration event, in minutes and volume fractions."""

    rt_min: float
    phi_outlet: float
    k_e: float
    flow_at_elution: float
    dphi_dt_outlet: float


def outlet_slope(program, time_min, void_ml, dwell_ml):
    """Differentiate outlet phi using h=min(0.01*t0_e, 0.001 min).

    At a step or segment boundary, disagreeing one-sided slopes select the
    post-event slope. Offset right samples avoid differentiating the jump itself.
    """
    t0_e = void_ml / program.flow(time_min)
    step = min(0.01 * t0_e, 0.001)

    def phi(offset):
        """Return outlet composition at an offset from elution."""
        return program.local_phi(time_min + offset, 1.0, void_ml, dwell_ml)

    left = (phi(-step / 2) - phi(-step)) / (step / 2)
    right = (phi(step) - phi(step / 2)) / (step / 2)
    central = (phi(step) - phi(-step)) / (2 * step)
    if not math.isclose(left, right, rel_tol=1e-5, abs_tol=1e-9):
        return right
    if not math.isclose(central, (left + right) / 2, rel_tol=1e-5, abs_tol=1e-9):
        return right
    return 0.0 if abs(central) < 1e-10 else central


def retention_state(req, compound, rtol=1e-7, max_step=None):
    """Solve the existing plug-flow migration ODE and return the outlet event."""
    from .retention_models import retention_model

    model = retention_model(compound)
    program = Program(req)
    void_ml = volume(req.column)
    end_min = program.t[-1]

    def derivative(time_min, position):
        """Return solute velocity in normalized column lengths per minute."""
        phi = program.local_phi(time_min, position[0], void_ml, req.mobile.dwell_ml)
        retention_factor = model.k(phi, req)
        return [program.flow(time_min) / (void_ml * (1 + retention_factor))]

    def eluted(time_min, position):
        """Locate the outlet crossing."""
        return position[0] - 1

    eluted.terminal = True
    eluted.direction = 1
    solution = solve_ivp(
        derivative,
        (0, end_min),
        [0.0],
        method='DOP853',
        events=eluted,
        rtol=rtol,
        atol=rtol * 1e-2,
        max_step=max_step or min(0.1, end_min / 80),
    )
    if not solution.success:
        raise ValueError('Migration solver failed')
    if not len(solution.t_events[0]):
        return None
    rt_min = float(solution.t_events[0][0])
    phi_outlet = program.local_phi(rt_min, 1.0, void_ml, req.mobile.dwell_ml)
    return RetentionState(
        rt_min=rt_min,
        phi_outlet=phi_outlet,
        k_e=model.k(phi_outlet, req),
        flow_at_elution=program.flow(rt_min),
        dphi_dt_outlet=outlet_slope(program, rt_min, void_ml, req.mobile.dwell_ml),
    )


def retention(req, compound, rtol=1e-7, max_step=None):
    """Keep the float-or-None interface used by calibration and existing callers."""
    state = retention_state(req, compound, rtol, max_step)
    return state.rt_min if state is not None else None


def band_width(req, compound, state, program):
    """Compute G*t0_e*(1+k_e)/sqrt(N); multi-segment: local approximation.

    Independently implemented from the requested equations. Reference: Poppe,
    Paanakker & Bronckhorst, J. Chromatogr. 204 (1981), 77-84,
    doi:10.1016/S0021-9673(00)81641-6. No upstream simulator code is used.
    Injection and extra-column variances retain the existing conventions.
    """
    from .retention_models import retention_model

    t0_e = volume(req.column) / state.flow_at_elution
    slope = state.dphi_dt_outlet
    b_e = t0_e * compound.s * math.log(10) * slope
    k_initial = retention_model(compound).k(program.composition(0), req)
    poppe_p = k_initial * b_e / (1 + k_initial)
    compression = 1.0
    warning = None
    if req.band_compression == 'poppe':
        if abs(1 + poppe_p) < 1e-12:
            warning = 'Local Poppe expression is singular; G=1 used for this peak.'
        else:
            compression = math.sqrt(1 + poppe_p + poppe_p**2 / 3) / abs(1 + poppe_p)
    sigma_col = compression * t0_e * (1 + state.k_e) / math.sqrt(req.column.plates)
    sigma_inj = req.mobile.injection_ul / 1000 / program.flow(0) / math.sqrt(12)
    sigma = math.sqrt(sigma_col**2 + sigma_inj**2 + req.mobile.extra_sigma_min**2)
    return {
        'sigma_col_min': sigma_col,
        'sigma_min': sigma,
        'compression_factor': compression,
        'b_e': b_e,
        'width_warning': warning,
    }


def eligibility(req,c):
 if req.mode!='RP':return 'unsupported',f'{req.mode}: independent quantitative model not enabled'
 if req.workflow=='structure':return 'insufficient_data','No compatible retention model for these structure/conditions'
 if c.kind in ['polymer','peptide','protein','oligomer']:return 'unsupported','No validated LSS model for this entity kind'
 if c.logkw is None or c.s is None:return 'insufficient_data','Missing logKw / S'
 if req.workflow=='calibrated' and c.source!='calibrated':return 'insufficient_data','No calibrated parameters for this component'
 from .conditions import scope_matches, scope_mismatches
 if c.scope and not scope_matches(c.scope,req):return 'insufficient_data','Incompatible retention scope: '+ '; '.join(scope_mismatches(c.scope,req))
 if c.parameter_origin in ['prediction','literature']:
  from .features import molecular_features
  if c.retention_provenance.get('scope') and not scope_matches(c.retention_provenance['scope'],req):return 'insufficient_data','Original model chemistry scope no longer matches'
  if not c.smiles or molecular_features(c.smiles)[0]['canonical_smiles']!=c.retention_provenance.get('canonical_smiles'):return 'insufficient_data','Structure changed since parameters were obtained'
  if c.retention_provenance.get('particle_um',req.column.particle_um)!=req.column.particle_um:return 'insufficient_data','Particle specification changed since prediction'
  limits=c.retention_provenance.get('phi_range')
  if limits and any(not limits[0]-1e-9<=n.b_percent/100<=limits[1]+1e-9 for n in req.gradient):return 'insufficient_data','Gradient outside the retention-curve organic-fraction range'
 return c.source,None

def simulate(req: Simulation, deadline=None):
    """Run migration, outlet-state bandwidth and area-normalized Gaussian signals."""
    from .prediction import prepare_structure
    from .mixture import signal_amounts

    original_input = req.model_dump()
    req, predictions = prepare_structure(req)
    signals = signal_amounts(req)
    program = Program(req)
    void_ml = volume(req.column)
    grid = np.linspace(0, program.t[-1], req.points)
    peaks = []
    curves = []
    warnings = []
    for compound in req.compounds:
        if deadline and time.monotonic() > deadline:
            raise TimeoutError('Computation budget exceeded')
        try:
            source, error = eligibility(req, compound)
        except ValueError as exc:
            source, error = 'insufficient_data', str(exc)
        row = {
            'simulation_status': 'ineligible' if error else 'pending',
            'id': compound.id,
            'name': compound.name,
            'source': source,
            'rt_min': None,
            'eluted': False,
            'warning': error,
            'sigma_min': None,
            'sigma_col_min': None,
            'fwhm_min': None,
            'width_base_min': None,
            'k_e': None,
            'phi_outlet': None,
            'compression_factor': None,
            **signals[compound.id],
            'peak_height': None,
            'retention_provenance': compound.retention_provenance,
            'parameter_scope': compound.scope.model_dump() if compound.scope else None,
        }
        if not error:
            state = retention_state(req, compound)
            row['eluted'] = state is not None
            row['simulation_status'] = 'eluted' if state is not None else 'non_eluted'
            if state is None:
                row['warning'] = 'Non-eluted within programmed run; not assigned a fictitious Rt'
            else:
                row.update(
                    rt_min=state.rt_min,
                    k_e=state.k_e,
                    phi_outlet=state.phi_outlet,
                    flow_at_elution=state.flow_at_elution,
                    dphi_dt_outlet=state.dphi_dt_outlet,
                )
                if req.column.plates:
                    widths = band_width(req, compound, state, program)
                    sigma = widths['sigma_min']
                    row.update({key: value for key, value in widths.items() if key != 'width_warning'})
                    row.update(
                        fwhm_min=2 * math.sqrt(2 * math.log(2)) * sigma,
                        width_base_min=4 * sigma,
                    )
                    if widths['width_warning']:
                        row['warning'] = widths['width_warning']
                    height = signals[compound.id]['peak_area'] / (math.sqrt(2 * math.pi) * sigma)
                    row['peak_height'] = height
                    curves.append({
                        'id': compound.id,
                        'name': compound.name,
                        'y': (height * np.exp(-0.5 * ((grid - state.rt_min) / sigma)**2)).tolist(),
                    })
                else:
                    row['warning'] = 'Efficiency missing: Rt only; peak / Rs not generated'
            if compound.scope is None:
                warnings.append(compound.name + ': parameter scope undeclared; supplied parameters used')
        peaks.append(row)
    ordered = sorted([row for row in peaks if row['eluted']], key=lambda row: row['rt_min'])
    pairs = []
    for first, second in zip(ordered, ordered[1:]):
        rs = None
        if first['width_base_min'] and second['width_base_min']:
            rs = 2 * (second['rt_min'] - first['rt_min']) / (first['width_base_min'] + second['width_base_min'])
        pairs.append({
            'ids': [first['id'], second['id']],
            'names': [first['name'], second['name']],
            'rs': rs,
            'coelution': rs is not None and rs < 1.5,
        })
        first['rs_to_next'] = rs
    if ordered:
        ordered[-1]['rs_to_next'] = None
    if any(row['sigma_min'] and grid[1] - grid[0] > row['sigma_min'] / 2 for row in peaks):
        warnings.append('Plot grid is coarse relative to some peak widths; use exported peak metrics')
    return {
        'input': original_input,
        'resolved_compounds': [compound.model_dump() for compound in req.compounds],
        'structure_predictions': predictions,
        'model': MODEL,
        'mode': req.mode,
        'peaks': peaks,
        'pairs': pairs,
        'order': [row['id'] for row in ordered],
        'min_rs': min((pair['rs'] for pair in pairs if pair['rs'] is not None), default=None),
        'time_min': grid.tolist(),
        'traces': curves,
        'gradient': {
            'program_b_percent': [100 * program.composition(t) for t in grid],
            'inlet_b_percent': [100 * program.local_phi(t, 0, void_ml, req.mobile.dwell_ml) for t in grid],
        },
        'void_ml': void_ml,
        'initial_t0_min': void_ml / program.flow(0),
        'total_solvent_ml': float(program.v[-1]),
        'warnings': list(dict.fromkeys(warnings)),
        'assumptions': [
            'Dilute local equilibrium LSS; plug-flow solvent transport; no overload',
            'Peak area = injected amount × relative response; Gaussian height = area / (sqrt(2π) sigma)',
            'Gradient band width: G*t0_e*(1+k_e)/sqrt(N); Poppe or G=1; pending user experimental checks',
            'Multi-segment gradients use a local outlet approximation; injection and extra-column variances are additive',
            'Specified pH / temperature / solvent do not independently modify LSS parameters',
        ],
        'uncertainty': {'quantified': False, 'reason': 'Pending user experimental checks'},
        'pressure': {'available': False, 'reason': 'Missing viscosity, permeability and instrument pressure model'},
    }


def optimize(req:Optimize):
 from .schemas import Node
 from .prediction import prepare_structure
 base,_=prepare_structure(req.simulation)
 failures=[]
 for c in base.compounds:
  try:reason=eligibility(base,c)[1]
  except ValueError as exc:reason=str(exc)
  if reason:failures.append(f'{c.name} ({c.id}): {reason}')
 if failures:raise ValueError('Optimization blocked: '+'; '.join(failures))
 if base.mode!='RP' or not base.column.plates or len(base.compounds)<2:raise ValueError('Optimization needs ≥2 eligible RP components and column efficiency')
 for c in base.compounds:
  limits=c.retention_provenance.get('phi_range') if c.parameter_origin in ['prediction','literature'] else None
  if limits and any(not limits[0]-1e-9<=v/100<=limits[1]+1e-9 for v in req.starts_percent+req.ends_percent):raise ValueError('Optimization candidate fractions exceed the retention model interval')
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
 first=methods[0];scope=(first.column.stationary_phase,first.mobile.b,first.mobile.ph,first.column.temperature_c,first.mobile.a,first.mobile.buffer,first.mobile.ph_control)
 if any((m.column.stationary_phase,m.mobile.b,m.mobile.ph,m.column.temperature_c,m.mobile.a,m.mobile.buffer,m.mobile.ph_control)!=scope for m in methods):raise ValueError('Calibration methods must share stationary phase, solvents, buffer, pH and temperature')
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
 return {'compound_id':req.compound_id,'logkw':float(fit.x[0]),'s':float(fit.x[1]),'source':'calibrated','scope':{'stationary_phase':scope[0],'mobile_b':scope[1],'ph':scope[2],'temperature_c':scope[3],'mobile_a':scope[4],'buffer':scope[5],'ph_control':scope[6]},'residuals_min':fit.fun.tolist(),'rmse_fit_min':float(np.sqrt(np.mean(fit.fun**2))),'jacobian_condition':float(np.linalg.cond(fit.jac)),'statistical_prediction_error':None,'warning':'Training fit residual is not external prediction accuracy; synthetic inputs remain synthetic','model':MODEL}

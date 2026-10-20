"""AGPL-3.0-or-later. Explicit units and capability boundaries for EluSim."""
from typing import Literal
from .sources import Source, source_code
from pydantic import BaseModel, Field, ConfigDict, model_validator

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)

class Column(Strict):
    efficiency_model: Literal['fixed', 'van_deemter'] = 'fixed'
    vd_a: float = Field(default=1.0, ge=0, le=100)
    vd_b: float = Field(default=2.0, gt=0, le=100)
    vd_c: float = Field(default=0.05, gt=0, le=100)
    diffusion_m2_s: float = Field(default=1.0e-9, gt=0, le=1.0e-6)
    flow_resistance: float = Field(default=500, gt=0, le=100000)
    manufacturer: str = Field(default='Generic', max_length=120)
    stationary_phase: str = Field(default='Generic C18', max_length=120)
    length_mm: float = Field(default=100, ge=5, le=1000)
    diameter_mm: float = Field(default=2.1, ge=.1, le=50)
    particle_um: float = Field(default=1.7, ge=.5, le=100)
    pore_angstrom: float = Field(default=100, ge=10, le=5000)
    porosity: float = Field(default=.68, gt=0, lt=1)
    void_ml: float | None = Field(default=None, gt=0, le=1000)
    plates: float | None = Field(default=12000, ge=100, le=1000000)
    temperature_c: float = Field(default=25, ge=0, le=100)

class Node(Strict):
    time_min: float = Field(ge=0, le=240)
    b_percent: float = Field(ge=0, le=100)
    flow_ml_min: float = Field(default=.3, ge=.01, le=20)
    temperature_c: float = Field(default=25, ge=0, le=100)
    interpolation: Literal['linear', 'step'] = 'linear'

class Mobile(Strict):
    mixer_ml: float = Field(default=0, ge=0, le=5)
    system_pressure_bar: float = Field(default=0, ge=0, le=500)
    a: str = Field(default='Water', max_length=120)
    b: Literal['ACN', 'MeOH'] = 'ACN'
    ph: float | None = Field(default=7, ge=0, le=14)
    ph_control: Literal['fixed', 'formulation'] = 'fixed'
    buffer: str = Field(default='None', max_length=120)
    injection_ul: float = Field(default=1, ge=0, le=1000)
    dwell_ml: float = Field(default=.1, ge=0, le=20)
    extra_sigma_min: float = Field(default=0, ge=0, le=10)

class Scope(Strict):
    stationary_phase: str = Field(default='Generic C18', max_length=120)
    mobile_a: str = Field(default='Water', max_length=120)
    buffer: str = Field(default='None', max_length=120)
    mobile_b: Literal['ACN', 'MeOH'] = 'ACN'
    ph: float | None = Field(default=7, ge=0, le=14)
    ph_control: Literal['fixed', 'formulation'] = 'fixed'
    temperature_c: float = Field(default=25, ge=0, le=100)

class Compound(Strict):
    id: str = Field(min_length=1, max_length=80)
    name: str = Field(max_length=160)
    kind: Literal['small_molecule','oligomer','polymer','peptide','protein','parameterized'] = 'small_molecule'
    smiles: str | None = Field(default=None, max_length=2000)
    sequence: str | None = Field(default=None, max_length=10000)
    logkw: float | None = Field(default=None, ge=-3, le=12)
    s: float | None = Field(default=None, ge=0, le=30)
    amplitude: float = Field(default=1, gt=0, le=100)
    mixture_parts: float = Field(default=1, ge=0, le=1000000)
    concentration: float | None = Field(default=None, ge=0, le=1000000)
    concentration_unit: Literal['mM', 'mg/mL'] = 'mM'
    response_factor: float = Field(default=1, ge=0, le=1000000)
    parameter_origin: Literal['manual', 'prediction', 'calibration', 'literature'] = 'manual'
    parameter_tier: Literal['A', 'B', 'C', 'D', 'M'] | None = None
    retention_provenance: dict = Field(default_factory=dict)
    source: Source = 'model_based'
    source_legacy: str | None = None

    @model_validator(mode='before')
    @classmethod
    def migrate_source(cls, data):
        if isinstance(data, dict) and 'source' in data:
            data=dict(data); original=data['source']; data['source']=source_code(original)
            if original!=data['source'] and original is not None:
                if data.get('source_legacy') is None:data['source_legacy']=str(original)
        return data
    scope: Scope | None = None
    mode_parameters: dict = Field(default_factory=dict)

class Simulation(Strict):
    max_pressure_bar: float | None = Field(default=None, gt=0, le=10000)
    solver: Literal['auto', 'ode', 'analytic'] = 'auto'
    band_compression: Literal['poppe', 'none'] = 'poppe'
    mode: Literal['RP','NP','HILIC','IEX','SEC'] = 'RP'
    workflow: Literal['known','calibrated','structure'] = 'known'
    compounds: list[Compound] = Field(min_length=1, max_length=20)
    column: Column = Field(default_factory=Column)
    mobile: Mobile = Field(default_factory=Mobile)
    gradient: list[Node] = Field(min_length=2, max_length=40)
    points: int = Field(default=1000, ge=100, le=2000)
    mixture_basis: Literal['parts', 'concentration'] = 'parts'

    @model_validator(mode='after')
    def valid_gradient(self):
        if self.gradient[0].time_min != 0: raise ValueError('Gradient must start at 0 min')
        if any(b.time_min <= a.time_min for a,b in zip(self.gradient,self.gradient[1:])): raise ValueError('Gradient times must strictly increase')
        if len({c.id for c in self.compounds}) != len(self.compounds): raise ValueError('Compound IDs must be unique')
        if any(n.temperature_c != self.column.temperature_c for n in self.gradient): raise ValueError('Temperature gradients need a validated temperature-dependent retention model; V1 supports constant temperature')
        return self

class Optimize(Strict):
    simulation: Simulation
    durations_min: list[float] = Field(default=[5,10,15,20], min_length=1, max_length=8)
    starts_percent: list[float] = Field(default=[5,15], min_length=1, max_length=5)
    ends_percent: list[float] = Field(default=[80,95], min_length=1, max_length=5)
    target_rs: float = Field(default=1.5, ge=.1, le=20)
    hold_min: float = Field(default=3, ge=0, le=30)
    max_solvent_ml: float | None = Field(default=None, gt=0, le=1000)

    @model_validator(mode='after')
    def budget(self):
        if len(self.durations_min)*len(self.starts_percent)*len(self.ends_percent)>24: raise ValueError('At most 24 candidate gradients')
        if any(t<=0 or t+self.hold_min>240 for t in self.durations_min): raise ValueError('Invalid duration')
        if any(not 0<=v<=100 for v in self.starts_percent+self.ends_percent): raise ValueError('B% out of bounds')
        return self

class Observation(Strict):
    method: Simulation
    rt_min: float = Field(gt=0, le=240)

class Calibration(Strict):
    observations: list[Observation] = Field(min_length=2, max_length=12)
    compound_id: str = Field(max_length=80)

class SearchRange(Strict):
    """An inclusive numeric grid axis."""

    min: float
    max: float
    steps: int = Field(ge=1, le=100)

    @model_validator(mode="after")
    def ordered(self):
        """Require ordered endpoints."""
        if self.max < self.min:
            raise ValueError("Grid maximum must be at least its minimum")
        return self


class OptimizeMap(Strict):
    """A bounded constant-flow resolution grid."""

    simulation: Simulation
    gradient_time_min: SearchRange = Field(default_factory=lambda: SearchRange(min=2, max=60, steps=30))
    start_percent: SearchRange = Field(default_factory=lambda: SearchRange(min=0, max=50, steps=11))
    end_percent: SearchRange = Field(default_factory=lambda: SearchRange(min=30, max=100, steps=15))
    initial_hold_min: float = Field(default=0, ge=0, le=60)
    final_hold_min: float = Field(default=3, ge=0, le=60)
    target_rs: float = Field(default=1.5, gt=0, le=100)
    max_run_time_min: float | None = Field(default=None, gt=0, le=240)

    @model_validator(mode="after")
    def bounded_grid(self):
        """Reject excessive work and nonconstant flow before process creation."""
        import numpy as np

        if len({node.flow_ml_min for node in self.simulation.gradient}) != 1:
            raise ValueError("地圖需定流速；請改用單次模擬")
        if not 0 < self.gradient_time_min.min <= self.gradient_time_min.max:
            raise ValueError("Gradient time must be positive")
        if self.gradient_time_min.max + self.initial_hold_min + self.final_hold_min > 240:
            raise ValueError("Total programmed run must not exceed 240 min")
        if not all(0 <= axis.min <= axis.max <= 100 for axis in (self.start_percent, self.end_percent)):
            raise ValueError("Composition bounds must be within 0–100 %B")
        starts = np.linspace(self.start_percent.min, self.start_percent.max, self.start_percent.steps)
        ends = np.linspace(self.end_percent.min, self.end_percent.max, self.end_percent.steps)
        count = int(np.sum(ends[None, :] > starts[:, None] + 1)) * self.gradient_time_min.steps
        cells = self.start_percent.steps * self.end_percent.steps * self.gradient_time_min.steps
        if self.simulation.mobile.mixer_ml > 0 and count > 2000:
            raise ValueError("混合器延遲啟用時，候選組合上限為 2,000")
        if count > 20000 or count * len(self.simulation.compounds) > 400000 or cells > 40000:
            raise ValueError("Grid limit: 20 000 candidates, 400 000 candidate-compound pairs, 40 000 stored cells")
        return self


class OptimizeMultiSegment(Strict):
    """Time-limited monotone two- or three-ramp search."""

    simulation: Simulation
    segments: Literal[2, 3] = 2
    min_segment_min: float = Field(default=0.5, ge=0.1, le=10)
    start_percent_bounds: tuple[float, float] = (0, 50)
    end_percent_bounds: tuple[float, float] = (30, 100)
    total_gradient_time_bounds: tuple[float, float] = (2, 60)
    initial_hold_min: float = Field(default=0, ge=0, le=60)
    final_hold_min: float = Field(default=3, ge=0, le=60)
    target_rs: float = Field(default=1.5, gt=0, le=100)
    max_run_time_min: float | None = Field(default=None, gt=0, le=240)
    seed: int = Field(default=42, ge=0, le=4294967295)
    time_budget_s: float = Field(default=20, gt=0, le=25)
    initial_candidate: list[Node] | None = Field(default=None, min_length=2, max_length=40)

    @model_validator(mode="after")
    def bounded_search(self):
        """Require constant flow and physically bounded search variables."""
        if len({node.flow_ml_min for node in self.simulation.gradient}) != 1:
            raise ValueError("Multi-segment search requires constant flow")
        for lower, upper in (self.start_percent_bounds, self.end_percent_bounds):
            if not 0 <= lower <= upper <= 100:
                raise ValueError("Composition bounds must be ordered within 0–100 %B")
        if self.start_percent_bounds[0] + 1 >= self.end_percent_bounds[1]:
            raise ValueError("No increasing gradient exists within the bounds")
        lower, upper = self.total_gradient_time_bounds
        lower = max(lower, self.segments * self.min_segment_min)
        self.total_gradient_time_bounds = (lower, upper)
        if lower <= 0 or lower > upper or upper + self.initial_hold_min + self.final_hold_min > 240:
            raise ValueError("Gradient time bounds exceed programmed run limits")
        return self

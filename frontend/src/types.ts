export type ParameterTier = "A" | "B" | "C" | "D" | "M";
import { sourceCode, type ParameterSource } from "./sources";
export type Node = {
  time_min: number;
  b_percent: number;
  flow_ml_min: number;
  temperature_c: number;
  interpolation: "linear" | "step";
};
export type Scope = {
  stationary_phase: string;
  mobile_a: string;
  buffer: string;
  mobile_b: "ACN" | "MeOH";
  ph: number | null;
  ph_control?: "fixed" | "formulation";
  temperature_c: number;
};
export type Compound = {
  parameter_tier?: ParameterTier | null;
  id: string;
  name: string;
  kind:
    | "small_molecule"
    | "parameterized"
    | "oligomer"
    | "polymer"
    | "peptide"
    | "protein";
  smiles: string | null;
  sequence?: string;
  logkw: number | null;
  s: number | null;
  amplitude: number;
  mixture_parts?: number;
  concentration?: number | null;
  concentration_unit?: "mM" | "mg/mL";
  response_factor?: number;
  parameter_origin?: "manual" | "prediction" | "calibration" | "literature";
  retention_provenance?: Record<string, unknown>;
  source: ParameterSource;
  source_legacy?: string | null;
  scope?: Scope | null;
  mode_parameters?: Record<string, unknown>;
  descriptors?: Descriptor;
};
export type Descriptor = {
  smiles: string;
  formula: string;
  mw: number;
  logp: number;
  tpsa: number;
  hbd: number;
  hba: number;
  svg: string;
  prediction_status: string;
};
export type Column = {
  manufacturer: string;
  stationary_phase: string;
  length_mm: number;
  diameter_mm: number;
  particle_um: number;
  pore_angstrom: number;
  porosity: number;
  void_ml: number | null;
  plates: number | null;
  temperature_c: number;
};
export type Config = {
  solver?: "auto" | "ode" | "analytic";
  band_compression?: "poppe" | "none";
  project_schema_version?: number;
  mixture_basis?: "parts" | "concentration";
  mode: string;
  workflow: "known" | "calibrated" | "structure";
  compounds: Compound[];
  column: Column;
  mobile: {
    a: string;
    b: "ACN" | "MeOH";
    ph: number | null;
    ph_control?: "fixed" | "formulation";
    buffer: string;
    injection_ul: number;
    dwell_ml: number;
    extra_sigma_min: number;
  };
  gradient: Node[];
  points: number;
};
export type Peak = {
  parameter_tier?: ParameterTier;
  k_e?: number | null;
  phi_outlet?: number | null;
  compression_factor?: number | null;
  rs_to_next?: number | null;
  simulation_status?: "ineligible" | "pending" | "eluted" | "non_eluted";
  mixture_fraction: number;
  injected_amount: number;
  amount_unit: string;
  peak_area: number;
  peak_height: number | null;
  id: string;
  name: string;
  source: ParameterSource;
  source_legacy?: string | null;
  rt_min: number | null;
  eluted: boolean;
  warning: string | null;
  sigma_min: number | null;
  fwhm_min: number | null;
  width_base_min: number | null;
};
export type Result = {
  resolved_compounds?: Compound[];
  structure_predictions?: Record<string, any>[];
  input: Config;
  model: string;
  mode: string;
  peaks: Peak[];
  pairs: {
    ids: string[];
    names: string[];
    rs: number | null;
    coelution: boolean;
  }[];
  order: string[];
  min_rs: number | null;
  time_min: number[];
  traces: { id: string; name: string; y: number[] }[];
  gradient: { program_b_percent: number[]; inlet_b_percent: number[] };
  void_ml: number;
  initial_t0_min: number;
  total_solvent_ml: number;
  warnings: string[];
  assumptions: string[];
  uncertainty: { quantified: boolean; reason: string };
  pressure: { available: boolean; reason: string };
};
export type Candidate = {
  gradient: Node[];
  feasible: boolean;
  all_eluted: boolean;
  min_rs: number | null;
  duration_min: number;
  solvent_ml: number;
  result: Result;
  limits: string[];
};
export const demo: Config = {
  mode: "RP",
  workflow: "known",
  compounds: [
    {
      id: "a",
      name: "Synthetic A",
      kind: "parameterized",
      smiles: null,
      logkw: 2,
      s: 4,
      amplitude: 1,
      source: "screening_only",
    },
    {
      id: "b",
      name: "Synthetic B",
      kind: "parameterized",
      smiles: null,
      logkw: 2.5,
      s: 4.5,
      amplitude: 0.8,
      source: "screening_only",
    },
    {
      id: "c",
      name: "Synthetic C",
      kind: "parameterized",
      smiles: null,
      logkw: 3,
      s: 5,
      amplitude: 1.1,
      source: "screening_only",
    },
  ],
  column: {
    manufacturer: "Generic",
    stationary_phase: "Generic C18",
    length_mm: 100,
    diameter_mm: 2.1,
    particle_um: 1.7,
    pore_angstrom: 100,
    porosity: 0.68,
    void_ml: null,
    plates: 12000,
    temperature_c: 25,
  },
  mobile: {
    a: "Water",
    b: "ACN",
    ph: 7,
    buffer: "None",
    injection_ul: 1,
    dwell_ml: 0.1,
    extra_sigma_min: 0,
  },
  gradient: [
    {
      time_min: 0,
      b_percent: 5,
      flow_ml_min: 0.3,
      temperature_c: 25,
      interpolation: "linear",
    },
    {
      time_min: 10,
      b_percent: 95,
      flow_ml_min: 0.3,
      temperature_c: 25,
      interpolation: "linear",
    },
    {
      time_min: 15,
      b_percent: 95,
      flow_ml_min: 0.3,
      temperature_c: 25,
      interpolation: "linear",
    },
  ],
  points: 1500,
};
/** Remove browser-only descriptor/project fields from the shared API payload. */
export function payload(config: Config) {
  const { project_schema_version, ...method } = config;
  return {
    ...method,
    compounds: config.compounds.map(({ descriptors, ...c }) => ({
      ...c,
      source: sourceCode(c.source),
    })),
  };
}

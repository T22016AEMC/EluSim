import type { Compound, Result } from "./types";
import { compoundTier } from "./retentionEstimates";

/** Quote CSV fields without changing the stored project values. */
function csv(headers: string[], rows: unknown[][]): string {
  const cell = (value: unknown) =>
    '"' + String(value ?? "").replaceAll('"', '""') + '"';
  return [
    headers.join(","),
    ...rows.map((row) => row.map(cell).join(",")),
  ].join("\r\n");
}

/** Export original parameter provenance and numeric descriptors for user checks. */
export function parameterCsv(compounds: Compound[]): string {
  return csv(
    [
      "id",
      "name",
      "smiles",
      "canonical_smiles",
      "logkw",
      "s",
      "tier",
      "parameter_source",
      "model_version",
      "warnings",
      "crippen_logp",
      "tpsa",
      "hbd",
      "aromatic_rings",
      "mw",
    ],
    compounds.map((compound) => {
      const provenance = compound.retention_provenance ?? {};
      const features = (provenance.features ?? {}) as Record<string, unknown>;
      return [
        compound.id,
        compound.name,
        compound.smiles,
        features.canonical_smiles ??
          provenance.canonical_smiles ??
          compound.descriptors?.smiles,
        compound.logkw,
        compound.s,
        compoundTier(compound),
        provenance.parameter_source ?? provenance.source,
        provenance.model_version,
        JSON.stringify(provenance.warnings ?? []),
        features.crippen_logp,
        features.tpsa,
        features.hbd,
        features.aromatic_rings,
        features.mw,
      ];
    }),
  );
}

/** Export outlet-state and width values actually returned by the solver. */
export function peakTableCsv(result: Result): string {
  return csv(
    [
      "id",
      "name",
      "tier",
      "rt_min",
      "k_e",
      "phi_outlet",
      "sigma_min",
      "compression_factor",
      "fwhm_min",
      "rs_to_next",
    ],
    result.peaks.map((peak) => [
      peak.id,
      peak.name,
      peak.parameter_tier,
      peak.rt_min,
      peak.k_e,
      peak.phi_outlet,
      peak.sigma_min,
      peak.compression_factor,
      peak.fwhm_min,
      peak.rs_to_next,
    ]),
  );
}

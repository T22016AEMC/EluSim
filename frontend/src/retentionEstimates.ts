import {
  useEffect,
  useRef,
  useState,
  type Dispatch,
  type SetStateAction,
} from "react";
import { api } from "./api";
import {
  payload,
  type Compound,
  type Config,
  type ParameterTier,
} from "./types";

export type Estimate = {
  logkw: number;
  s: number;
  tier: "A" | "B" | "C";
  tier_label: string;
  warnings: string[];
  condition_differences: string[];
  parameter_source: string;
  model_version: string;
  model_id: string;
  validation_status: string;
  features: Record<string, unknown>;
  scope: NonNullable<Compound["scope"]>;
  phi_range: number[];
  particle_um: number;
  license: string;
  reference: unknown;
};

/** Infer legacy tiers without upgrading any parameter's provenance. */
export function compoundTier(compound: Compound): ParameterTier {
  if (
    compound.parameter_origin === "calibration"
  )
    return "D";
  if (compound.parameter_tier) return compound.parameter_tier;
  if (compound.parameter_origin === "literature") return "A";
  if (compound.parameter_origin === "prediction") return "B";
  return "M";
}

/** Include all supplied LC conditions in stale-result and refresh checks. */
function methodKey(config: Config): string {
  return JSON.stringify([
    config.mode,
    config.column,
    config.mobile,
    config.gradient,
  ]);
}

/** Existing manual and calibrated values never enter background estimation. */
function automatic(compound: Compound): boolean {
  if (!compound.smiles || compound.kind !== "small_molecule") return false;
  if (compound.parameter_tier === "M" || compoundTier(compound) === "D")
    return false;
  if (["A", "B", "C"].includes(compoundTier(compound))) return true;
  return compound.logkw == null && compound.s == null;
}

/** Store parameters, structure and source conditions on the same Compound ID. */
export function applyEstimate(
  compound: Compound,
  estimate: Estimate,
): Compound {
  return {
    ...compound,
    logkw: estimate.logkw,
    s: estimate.s,
    parameter_tier: estimate.tier,
    parameter_origin: estimate.tier === "A" ? "literature" : "prediction",
    source:
      estimate.tier === "A"
        ? "literature_derived"
        : estimate.tier === "B"
          ? "experimental_model_prediction"
          : "screening_only",
    scope: estimate.scope,
    retention_provenance: {
      ...estimate,
      canonical_smiles: estimate.features.canonical_smiles,
      source: estimate.parameter_source,
    },
  };
}

/** Debounce shared compound estimates and reject responses for edited inputs. */
export function useRetentionEstimates(
  config: Config,
  setConfig: Dispatch<SetStateAction<Config>>,
  onError: (message: string) => void,
) {
  const current = useRef(config);
  current.current = config;
  const completed = useRef(new Map<string, string>());
  const failed = useRef(new Map<string, string>());
  const inFlight = useRef(new Map<string, Promise<void>>());
  const [running, setRunning] = useState(0);
  const conditions = methodKey(config);
  const structures = JSON.stringify(
    config.compounds.map((compound) => [
      compound.id,
      compound.smiles,
      compound.kind,
      compound.parameter_tier,
      compound.parameter_origin,
      compound.logkw == null,
      compound.s == null,
    ]),
  );

  /** Fetch one ID, preserving edits or condition changes made during the request. */
  async function estimateOne(id: string, force = false): Promise<void> {
    const snapshot = current.current;
    const original = snapshot.compounds.find((compound) => compound.id === id);
    if (
      !original?.smiles ||
      snapshot.mode !== "RP" ||
      compoundTier(original) === "D"
    )
      return;
    if (!force && !automatic(original)) return;
    const key = JSON.stringify([original.smiles, methodKey(snapshot)]);
    if (
      !force &&
      (completed.current.get(id) === key || failed.current.get(id) === key)
    )
      return;
    const requestId = JSON.stringify([id, key]);
    const existing = inFlight.current.get(requestId);
    if (existing) return existing;
    const originalParameters = JSON.stringify([
      original.logkw,
      original.s,
      original.parameter_tier,
      original.parameter_origin,
    ]);
    const task = (async () => {
      setRunning((value) => value + 1);
      try {
        const estimate = await api<Estimate>("retention/estimate", {
          smiles: original.smiles,
          method: payload(snapshot),
        });
        setConfig((latest) => {
          const target = latest.compounds.find(
            (compound) => compound.id === id,
          );
          if (
            !target ||
            target.smiles !== original.smiles ||
            methodKey(latest) !== methodKey(snapshot)
          )
            return latest;
          if (
            JSON.stringify([
              target.logkw,
              target.s,
              target.parameter_tier,
              target.parameter_origin,
            ]) !== originalParameters
          )
            return latest;
          if (compoundTier(target) === "D" || (!force && !automatic(target)))
            return latest;
          completed.current.set(id, key);
          failed.current.delete(id);
          return {
            ...latest,
            compounds: latest.compounds.map((compound) =>
              compound.id === id ? applyEstimate(compound, estimate) : compound,
            ),
          };
        });
      } catch (error) {
        failed.current.set(id, key);
        onError(original.name + ": " + (error as Error).message);
      } finally {
        inFlight.current.delete(requestId);
        setRunning((value) => value - 1);
      }
    })();
    inFlight.current.set(requestId, task);
    return task;
  }

  useEffect(() => {
    if (config.mode !== "RP") return;
    const timer = setTimeout(() => {
      void (async () => {
        for (const compound of current.current.compounds)
          await estimateOne(compound.id);
      })();
    }, 600);
    return () => clearTimeout(timer);
  }, [conditions, structures]);

  /** Refresh estimated records only; explicit M and D records are untouched. */
  async function estimateAll(): Promise<void> {
    for (const compound of current.current.compounds) {
      if (["A", "B", "C"].includes(compoundTier(compound)))
        await estimateOne(compound.id, true);
    }
  }

  const scheduled =
    config.mode === "RP" &&
    config.compounds.some((compound) => {
      if (!automatic(compound)) return false;
      const key = JSON.stringify([compound.smiles, conditions]);
      return (
        completed.current.get(compound.id) !== key &&
        failed.current.get(compound.id) !== key
      );
    });
  /** Query fresh refs when a queued simulation follows a method edit. */
  function isPending(): boolean {
    const latest = current.current;
    return (
      inFlight.current.size > 0 ||
      (latest.mode === "RP" &&
        latest.compounds.some((compound) => {
          if (!automatic(compound)) return false;
          const key = JSON.stringify([compound.smiles, methodKey(latest)]);
          return (
            completed.current.get(compound.id) !== key &&
            failed.current.get(compound.id) !== key
          );
        }))
    );
  }
  return {
    estimating: running > 0 || scheduled,
    estimateOne,
    estimateAll,
    isPending,
  };
}

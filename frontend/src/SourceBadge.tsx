import { tierLabel, tierExplanation, t } from "./i18n/zh-TW";
import { compoundTier } from "./retentionEstimates";
import type { Compound, Config } from "./types";

/** Display source descriptions without offering a provenance-editing control. */
export function SourceBadge({ compound }: { compound: Compound }) {
  const tier = compoundTier(compound);
  const warnings = (compound.retention_provenance?.warnings ?? []) as string[];
  return (
    <span
      className="pill source-badge"
      data-testid={"tier-" + compound.id}
      title={[
        tierExplanation(tier),
        ...warnings.map((warning) => t(warning)),
      ].join("\n")}
    >
      {tierLabel(tier)}
    </span>
  );
}

/** Explain a calculation precondition next to its compound, without changing inputs. */
export function CompoundIssue({
  compound,
  config,
}: {
  compound: Compound;
  config: Config;
}) {
  let reason = "";
  if (config.mode !== "RP") reason = t("unsupported_mode");
  else if (["peptide", "protein", "polymer"].includes(compound.kind))
    reason = t("unsupported_kind");
  else if (compound.logkw == null || compound.s == null)
    reason = t("no_parameters");
  else if (
    !Number.isFinite(compound.logkw) ||
    !Number.isFinite(compound.s) ||
    compound.logkw < -3 ||
    compound.logkw > 12 ||
    compound.s < 0 ||
    compound.s > 30
  )
    reason = t("invalid_parameters");
  return reason ? (
    <p className="warn" data-testid={"issue-" + compound.id}>
      {reason}
    </p>
  ) : null;
}

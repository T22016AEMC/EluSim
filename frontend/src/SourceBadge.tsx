import { tierLabel, tierExplanation, t } from "./i18n/zh-TW";
import { compoundTier } from "./retentionEstimates";
import type { Compound } from "./types";

/** Display source descriptions without offering a provenance-editing control. */
export function SourceBadge({ compound }: { compound: Compound }) {
  const tier = compoundTier(compound);
  const warnings = (compound.retention_provenance?.warnings ?? []) as string[];
  return (
    <span
      className="pill source-badge"
      data-testid={"tier-" + compound.id}
      title={[tierExplanation(tier), ...warnings.map((warning) => t(warning))].join("\n")}
    >
      {tierLabel(tier)}
    </span>
  );
}

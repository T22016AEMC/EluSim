import { t } from "./i18n/zh-TW";

export const sourceLabels = {
  measured: "Measured",
  calibrated: "Calibrated",
  model_based: "Model-based",
  screening_only: "Screening only",
  insufficient_data: "Insufficient data",
  unsupported: "Unsupported",
  experimental: "Experimental",
  literature_derived: "Literature-derived",
  validated_model_prediction:
    "Model prediction (legacy label; pending user review)",
  experimental_model_prediction: "Experimental model prediction",
  qualitative_screening: "Qualitative screening",
  unknown_legacy: "Unknown / Legacy",
} as const;
export type ParameterSource = keyof typeof sourceLabels;
const aliases: Record<string, ParameterSource> = Object.fromEntries(
  Object.entries(sourceLabels).map(([code, label]) => [
    label.toLowerCase(),
    code,
  ]),
) as Record<string, ParameterSource>;
Object.assign(aliases, {
  // Preserve the old wire label for migration, without displaying it as a claim.
  "validated model prediction": "validated_model_prediction",
  基於模型: "model_based",
  基于模型: "model_based",
  實測: "measured",
  实测: "measured",
  已校正: "calibrated",
  校正: "calibrated",
  僅供篩選: "screening_only",
  資料不足: "insufficient_data",
  不支援: "unsupported",
  未知: "unknown_legacy",
  legacy: "unknown_legacy",
  unknown: "unknown_legacy",
});

/** Map legacy UI labels to stable codes while retaining unknown provenance. */
export function sourceCode(value: unknown): ParameterSource {
  if (typeof value !== "string") return "unknown_legacy";
  const code = value.trim();
  return Object.hasOwn(sourceLabels, code)
    ? (code as ParameterSource)
    : aliases[code.toLowerCase()] || "unknown_legacy";
}

/** Display a label independently of the stored API code. */
export function sourceLabel(value: unknown) {
  return t(sourceLabels[sourceCode(value)]);
}

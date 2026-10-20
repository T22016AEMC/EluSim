"""Build the single frontend catalog and its backend presentation copy."""
import json
from pathlib import Path

root = Path(".")
translations = {}
for line in (root / "review/phase2.2/translations.tsv").read_text(encoding="utf-8-sig").splitlines():
    if line.strip():
        key, value = line.split("\t", 1)
        translations[key] = value
destination = root / "frontend/src/i18n"
destination.mkdir(exist_ok=True)
catalog = json.dumps(translations, ensure_ascii=False, indent=2)
helpers = """
/** Translate display text without changing API identifiers or user names. */
export function t(key: string, solvent = "ACN"): string {
  return (zhTW[key] ?? key).replaceAll("{solvent}", solvent);
}

/** Present parameter source codes only as descriptive labels. */
export function tierLabel(tier?: string | null): string {
  return t("source_" + (tier || "M"));
}

/** Return the explanation attached to a source badge. */
export function tierExplanation(tier: string): string {
  return t("source_explanation_" + tier);
}

/** Match field explanations independently of the current organic solvent. */
export function fieldHelp(label: string): string {
  const fields: [string, string][] = [
    ["Gradient time (min)", "help_gradient"],
    ["Start %B", "help_start"], ["End %B", "help_end"],
    ["Initial hold (min)", "help_initial"], ["Final hold (min)", "help_final"],
    ["Target minimum Rs", "help_rs"], ["Maximum analysis time (min)", "help_maximum"],
    ["Segments", "help_segments"], ["Search time budget (s)", "help_budget"],
    ["Minimum segment duration (min)", "help_minimum"],
  ];
  const match = fields.find(([key]) =>
    label.startsWith(t(key, "ACN")) || label.startsWith(t(key, "MeOH")),
  );
  return match ? t(match[1]) : "";
}
"""
(destination / "zh-TW.ts").write_text(
    "/** Taiwan Traditional Chinese presentation catalog. */\n"
    + "export const zhTW: Record<string, string> = " + catalog + ";\n" + helpers,
    encoding="utf-8",
)
(root / "backend/elusim/zh_tw.json").write_text(catalog + "\n", encoding="utf-8")

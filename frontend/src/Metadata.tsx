import { t } from "./i18n/zh-TW";

/** Show provenance and descriptors without embedding raw executable or SVG data. */
export function Metadata({ value }: { value: unknown }) {
  if (value == null) return <span>{t("null")}</span>;
  if (typeof value === "string") return <span>{t(value)}</span>;
  if (typeof value === "boolean") return <span>{t(String(value))}</span>;
  if (typeof value === "number") return <span>{String(value)}</span>;
  if (Array.isArray(value)) {
    if (value.every((item) => typeof item === "number")) {
      return <span>{value.join(", ")}</span>;
    }
    return <ul>{value.map((item, index) => <li key={index}><Metadata value={item} /></li>)}</ul>;
  }
  return <dl className="metadata">{Object.entries(value as Record<string, unknown>)
    .filter(([key]) => !["svg", "structure_svg", "fingerprint", "train_smiles"].includes(key))
    .map(([key, item]) => <div key={key}><dt>{t(key)}</dt><dd><Metadata value={item} /></dd></div>)}</dl>;
}

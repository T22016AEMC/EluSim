import { emptyProject, demo, type Config, type Compound } from "./types";
import { sourceCode } from "./sources";
import { t } from "./i18n/zh-TW";

export const PROJECT_VERSION = 3;

/** Preserve structures and parameters while retiring the legacy workflow gate. */
export function migrateProject(input: unknown): Config {
  if (!input || typeof input !== "object") {
    throw Error(
      t(
        "Invalid saved project: expected an object. Original storage retained.",
      ),
    );
  }
  const raw = input as Record<string, any>;
  if (!Array.isArray(raw.compounds) || !Array.isArray(raw.gradient)) {
    throw Error(
      t(
        "Invalid saved project: compounds and gradient are required. Original storage retained.",
      ),
    );
  }
  const ids = new Set<string>();
  let next = Number.isSafeInteger(raw.next_compound_number)
    ? Math.max(1, raw.next_compound_number)
    : 1;
  const usedNames = new Set(
    raw.compounds.map((compound: any) => compound?.name).filter(Boolean),
  );
  const compounds = raw.compounds.map((compound: any) => {
    if (!compound || typeof compound !== "object") {
      throw Error(t("Invalid compound record; original project retained."));
    }
    let id =
      typeof compound.id === "string" && compound.id.trim()
        ? compound.id
        : crypto.randomUUID();
    if (ids.has(id)) id = crypto.randomUUID();
    ids.add(id);
    const source = sourceCode(compound.source);
    let name = typeof compound.name === "string" ? compound.name.trim() : "";
    if (!name) {
      while (
        usedNames.has(t("compound_name").replace("{number}", String(next)))
      )
        next++;
      name = t("compound_name").replace("{number}", String(next++));
      usedNames.add(name);
    }
    const origin =
      compound.parameter_origin ??
      (compound.parameter_tier === "D"
        ? "calibration"
        : compound.parameter_tier === "A"
          ? "literature"
          : ["B", "C"].includes(compound.parameter_tier)
            ? "prediction"
            : "manual");
    return {
      ...compound,
      id,
      name,
      source,
      ...(compound.source !== undefined && compound.source !== source
        ? { source_legacy: compound.source_legacy ?? String(compound.source) }
        : {}),
      parameter_origin: origin,
      mixture_parts: compound.mixture_parts ?? 1,
      response_factor: compound.response_factor ?? 1,
    } as Compound;
  });
  return {
    ...raw,
    project_schema_version: PROJECT_VERSION,
    next_compound_number: next,
    compounds,
    column: { ...demo.column, ...raw.column },
    mobile: { ...demo.mobile, ...raw.mobile },
    gradient: raw.gradient.map((node: any) => ({
      ...node,
      interpolation: node.interpolation ?? "linear",
    })),
    mode: raw.mode ?? "RP",
    workflow: "known",
    points: raw.points ?? 1500,
  } as Config;
}

/** Read existing storage without deleting it, including malformed projects. */
export function loadProject(storage: Storage): {
  config: Config;
  error: string;
} {
  const original = storage.getItem("elusim-project");
  if (!original) return { config: emptyProject(), error: "" };
  try {
    const config = migrateProject(JSON.parse(original));
    if (
      JSON.stringify(config) !== original &&
      !storage.getItem("elusim-project-before-zhTW-migration")
    ) {
      storage.setItem("elusim-project-before-zhTW-migration", original);
    }
    return { config, error: "" };
  } catch (error) {
    return {
      config: emptyProject(),
      error:
        error instanceof SyntaxError ? t("Invalid saved JSON") : String(error),
    };
  }
}

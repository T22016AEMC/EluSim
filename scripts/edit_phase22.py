from pathlib import Path

path = Path("backend/elusim/engine.py")
text = path.read_text(encoding="utf-8")
text = text.replace(
    "    if req.workflow == 'calibrated' and compound.source != 'calibrated':\n"
    "        return 'insufficient_data', 'No calibrated parameters for this component'\n", "",
)
path.write_text(text, encoding="utf-8")
path = Path("backend/elusim/prediction.py")
text = path.read_text(encoding="utf-8")
text = text.replace("if req.workflow != 'structure' or req.mode != 'RP':", "if req.mode != 'RP':")
text = text.replace(
    '"""Acquire tiered LSS estimates for the structure workflow without scope gates."""',
    '"""Acquire automatic sources independently of the legacy workflow value."""',
)
path.write_text(text, encoding="utf-8")
path = Path("backend/elusim/estimation.py")
text = path.read_text(encoding="utf-8").replace(
    "if compound.parameter_origin == 'calibration' or compound.source == 'calibrated':",
    "if compound.parameter_origin == 'calibration':",
)
path.write_text(text, encoding="utf-8")
path = Path("backend/elusim/retention_registry.py")
text = path.read_text(encoding="utf-8").replace(
    "        tier = parameter_tier(compound)\n",
    """        tier = parameter_tier(compound)
        source = {
            'A': 'literature_derived', 'B': 'experimental_model_prediction',
            'C': 'screening_only', 'D': 'calibrated', 'M': 'model_based',
        }[tier]
        compound = compound.model_copy(update={'source': source})
""",
)
path.write_text(text, encoding="utf-8")

path = Path("frontend/src/types.ts")
text = path.read_text(encoding="utf-8")
text = text.replace('  project_schema_version?: number;', '  project_schema_version?: number;\n  next_compound_number?: number;')
text = text.replace('name: "Synthetic A"', 'name: "示範化合物 1"').replace('name: "Synthetic B"', 'name: "示範化合物 2"').replace('name: "Synthetic C"', 'name: "示範化合物 3"')
text = text.replace('const { project_schema_version, ...method } = config;', 'const { project_schema_version, next_compound_number, ...method } = config;')
text += '''
/** Start without scientific example values; legacy browser projects are retained. */
export function emptyProject(): Config {
  return { ...structuredClone(demo), compounds: [], next_compound_number: 1 };
}

/** Reserve a monotonically increasing fallback name within the browser project. */
export function nextCompoundName(config: Config): { name: string; next: number } {
  const used = new Set(config.compounds.map((compound) => compound.name));
  const existingNumbers = config.compounds.map((compound) =>
    Number(/^化合物 (\\d+)$/.exec(compound.name)?.[1] ?? 0),
  );
  let number = Math.max(config.next_compound_number ?? 1, ...existingNumbers.map((value) => value + 1));
  while (used.has("化合物 " + number)) number++;
  return { name: "化合物 " + number, next: number + 1 };
}

/** Names are presentation data; changes do not invalidate numerical results. */
export function calculationKey(config: Config): string {
  const method = payload(config);
  return JSON.stringify({
    ...method,
    compounds: method.compounds.map(({ name, ...compound }) => compound),
  });
}

/** Join current names by stable ID while preserving all calculated numbers. */
export function namedResult(result: Result, compounds: Compound[]): Result {
  const names = new Map(compounds.map((compound) => [compound.id, compound.name]));
  return {
    ...result,
    peaks: result.peaks.map((peak) => ({ ...peak, name: names.get(peak.id) ?? peak.name })),
    traces: result.traces.map((trace) => ({ ...trace, name: names.get(trace.id) ?? trace.name })),
    pairs: result.pairs.map((pair) => ({ ...pair, names: pair.ids.map((id, index) => names.get(id) ?? pair.names[index]) })),
    input: { ...result.input, compounds: result.input.compounds.map((compound) => ({ ...compound, name: names.get(compound.id) ?? compound.name })) },
  };
}
'''
path.write_text(text, encoding="utf-8")
path = Path("frontend/src/retentionEstimates.ts")
text = path.read_text(encoding="utf-8").replace(
    '    compound.parameter_origin === "calibration" ||\n    compound.source === "calibrated"',
    '    compound.parameter_origin === "calibration"',
)
path.write_text(text, encoding="utf-8")

path = Path("frontend/src/main.tsx")
text = path.read_text(encoding="utf-8")
text = 'import { SourceBadge } from "./SourceBadge";\n' + text
text = text.replace('  demo,\n', '  demo,\n  emptyProject,\n  nextCompoundName,\n  calculationKey,\n  namedResult,\n')
text = text.replace('const configKey = JSON.stringify(config);', 'const configKey = calculationKey(config);')
text = text.replace('[result, setResult] = useState<Result>()', '[rawResult, setResult] = useState<Result>()')
text = text.replace('[previous, setPrevious] = useState<Result>()', '[rawPrevious, setPrevious] = useState<Result>()')
text = text.replace('  const estimates = useRetentionEstimates', '  const result = rawResult ? namedResult(rawResult, config.compounds) : undefined;\n  const previous = rawPrevious ? namedResult(rawPrevious, config.compounds) : undefined;\n  const estimates = useRetentionEstimates', 1)
text = text.replace('const inputKey = JSON.stringify(current.current);', 'const inputKey = calculationKey(current.current);')
text = text.replace('          current.current.workflow === "structure" &&\n', '')
text = text.replace('appliedKey = JSON.stringify(next);', 'appliedKey = calculationKey(next);')
text = text.replace('  const simulate = async (jump = true) => {', '  const simulate = async (jump = true) => {\n    if (!current.current.compounds.length) { setTab(0); return; }')
text = text.replace('    change({\n      compounds: [\n        ...current.current.compounds,', '    const generated = nextCompoundName(current.current);\n    change({\n      next_compound_number: name.trim() ? current.current.next_compound_number : generated.next,\n      compounds: [\n        ...current.current.compounds,', 1)
text = text.replace('name: name || "New compound",', 'name: name.trim() || generated.name,')
# Remove only the workflow UI block.
start = text.index('              <div className="field-grid">\n                <label>\n                  Workflow')
end = text.index('              <div className="compound-grid">', start)
text = text[:start] + text[end:]
start = text.index('                      <label>\n                        Parameter source')
end = text.index('                    </div>', start)
text = text[:start] + text[end:]
start = text.index('                    <span\n                      className="pill"\n                      data-testid={"tier-"')
end = text.index('                    <button', start)
text = text[:start] + '                    <SourceBadge compound={c} />\n' + text[end:]
# Move the source badge directly after the name field.
text = text.replace('                    <SourceBadge compound={c} />\n', '')
text = text.replace('                      <button\n                        className="icon"', '                      <SourceBadge compound={c} />\n                      <button\n                        className="icon"', 1)
text = text.replace('''                                  {p.parameter_tier}
                                  {p.parameter_tier === "C" ? " 估算" : ""}''', '                                  {tierLabel(p.parameter_tier)}')
text = text.replace('import { SourceBadge }', 'import { tierLabel } from "./i18n/zh-TW";\nimport { SourceBadge }', 1)
text = text.replace('setConfig(structuredClone(demo));', 'setConfig(emptyProject());')
text = text.replace('disabled={!!busy || estimates.estimating}', 'disabled={!!busy || estimates.estimating || !config.compounds.length}')
text = text.replace('                <h2>Build your mixture</h2>', '''                <h2>Build your mixture</h2>
                <button className="secondary" onClick={() => {
                  change({ ...structuredClone(demo), next_compound_number: 1 });
                  setResult(undefined);
                  setSimulationAttempted(false);
                }}>Load demo mixture</button>''', 1)
text = text.replace('        {tab === 3 && (\n          <>', '''        {tab === 3 && (
          <>
            {!config.compounds.length && <p>{t("empty_compounds")}</p>}''', 1)
text = text.replace('              <h3>Mode-specific parameter requirements</h3>', '''              <p>{t("report0259_info")}</p>
              <h3>Mode-specific parameter requirements</h3>''', 1)
path.write_text(text, encoding="utf-8")

import { t as tr } from "./i18n/zh-TW";
import { tierLabel } from "./i18n/zh-TW";
import { Metadata } from "./Metadata";
import { SourceBadge } from "./SourceBadge";
import { OptimizationWorkspace } from "./OptimizationWorkspace";
import { compoundTier, useRetentionEstimates } from "./retentionEstimates";
import { parameterCsv, peakTableCsv } from "./retentionExports";
import React, { useState, useEffect, useRef, useCallback } from "react";
import { createRoot } from "react-dom/client";
import { Chart, GradientProfile } from "./Chart";
import { api } from "./api";
import { loadProject, migrateProject } from "./project";
import {
  sourceCode,
  sourceLabel,
  sourceLabels,
  type ParameterSource,
} from "./sources";
import { ModelConditions } from "./ModelConditions";
import { StructureEditor } from "./StructureEditor";
import {
  demo,
  emptyProject,
  nextCompoundName,
  calculationKey,
  namedResult,
  payload,
  type Config,
  type Compound,
  type Descriptor,
  type Result,
  type Scope,
} from "./types";
import "./style.css";
import { RetentionWorkspace } from "./RetentionWorkspace";
import { UVWorkspace } from "./UVWorkspace";
const tabs = [
  tr("Compounds"),
  tr("LC Mode & Column"),
  tr("Mobile Phase & Gradient"),
  tr("Chromatogram Simulation"),
  tr("Gradient Optimization"),
  tr("Experimental Calibration"),
  tr("Model & Column Library"),
  tr("Retention Prediction"),
  tr("UV-Vis / DAD"),
];
/** Download a browser-local project or export without server-side sharing. */
function download(name: string, content: string, type = "application/json") {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
const fmt = (n: number | null | undefined) => (n == null ? "—" : n.toFixed(3));
/** Render the existing numeric editor with optional null values. */
function Num({
  label,
  value,
  onChange,
  nullable = false,
  disabled = false,
}: {
  label: string;
  value: number | null;
  onChange: (n: number | null) => void;
  nullable?: boolean;
  disabled?: boolean;
}) {
  return (
    <label>
      {label}
      <input
        type="number"
        disabled={disabled}
        step="any"
        aria-label={label}
        value={value ?? ""}
        onChange={(e) =>
          onChange(
            e.target.value === "" && nullable ? null : Number(e.target.value),
          )
        }
      />
    </label>
  );
}
/** Render the existing workspaces and shared compound/method state. */
function App() {
  const [loaded] = useState(() => loadProject(localStorage));
  const [config, setConfig] = useState<Config>(loaded.config),
    [storageError, setStorageError] = useState(loaded.error),
    [resultKey, setResultKey] = useState(""),
    [simulationAttempted, setSimulationAttempted] = useState(false);
  const configKey = calculationKey(config);
  const [tab, setTab] = useState(0),
    [rawResult, setResult] = useState<Result>(),
    [rawPrevious, setPrevious] = useState<Result>(),
    [overlay, setOverlay] = useState(false),
    [busy, setBusy] = useState(""),
    [error, setError] = useState(""),
    [auto, setAuto] = useState(false),
    [selected, setSelected] = useState(""),
    [name, setName] = useState(""),
    [smiles, setSmiles] = useState(""),
    [descriptor, setDescriptor] = useState<Descriptor>(),
    [calibrationText, setCalibrationText] = useState(""),
    [calibrationResult, setCalibrationResult] =
      useState<Record<string, unknown>>(),
    [observations, setObservations] = useState<unknown[]>([]),
    [health, setHealth] = useState(tr("Connecting")),
    [modeParams, setModeParams] = useState("{}"),
    [replaceManual, setReplaceManual] = useState(false),
    [retentionRecords, setRetentionRecords] = useState<Record<string, any>[]>(
      [],
    ),
    [batchParts, setBatchParts] = useState("");
  const result = rawResult ? namedResult(rawResult, config.compounds) : undefined;
  const previous = rawPrevious ? namedResult(rawPrevious, config.compounds) : undefined;
  const estimates = useRetentionEstimates(config, setConfig, setError);
  const queuedSimulation = useRef<boolean | null>(null);
  const seq = useRef(0);
  const request = useRef<AbortController | null>(null);
  const current = useRef(config);
  current.current = config;
  useEffect(() => {
    api<{ rdkit: string }>("health")
      .then((h) => setHealth((tr("Python / RDKit") + " ") + h.rdkit))
      .catch(() => setHealth(tr("Backend unavailable")));
  }, []);
  useEffect(() => {
    if (!storageError)
      localStorage.setItem("elusim-project", JSON.stringify(config));
    seq.current++;
    request.current?.abort();
    setBusy((b) => (b === tr("Simulating") ? "" : b));
    if (!auto) return;
    const timer = setTimeout(() => void simulate(false), 700);
    return () => clearTimeout(timer);
  }, [config, auto, storageError, estimates.estimating]);
  useEffect(() => {
    if (queuedSimulation.current !== null && !estimates.isPending()) {
      const jump = queuedSimulation.current;
      queuedSimulation.current = null;
      void simulate(jump);
    }
  }, [config, estimates.estimating]);
  /** Apply a method or compound edit without keeping stale resolution messages. */
  const change = (update: Partial<Config>) => {
    setRetentionRecords([]);
    setConfig((c) => ({ ...c, ...update }));
  };
  /** Wait for parameter estimation, then submit the current method to the solver. */
  const simulate = async (jump = true) => {
    if (!current.current.compounds.length) { setTab(0); return; }
    if (estimates.isPending()) {
      if (jump) queuedSimulation.current = jump;
      return;
    }
    const token = ++seq.current;
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    const inputKey = calculationKey(current.current);
    setSimulationAttempted(true);
    if (jump) setTab(3);
    setResult(undefined);
    setBusy(tr("Simulating"));
    setError("");
    try {
      const r = await api<Result>(
        "simulate",
        payload(current.current),
        controller.signal,
      );
      if (token === seq.current) {
        let appliedKey = inputKey;
        if (
          r.resolved_compounds &&
          r.structure_predictions?.some((p) => p.logkw != null && p.s != null)
        ) {
          const next: Config = {
            ...current.current,
            workflow: "known",
            compounds: r.resolved_compounds.map((c) => ({
              ...c,
              descriptors: current.current.compounds.find((x) => x.id === c.id)
                ?.descriptors,
            })),
          };
          setConfig(next);
          setRetentionRecords(r.structure_predictions);
          appliedKey = calculationKey(next);
        }
        setPrevious(result);
        setResult(r);
        setResultKey(appliedKey);
        if (jump) setTab(3);
      }
    } catch (e) {
      if (token === seq.current && (e as Error).name !== "AbortError")
        setError((e as Error).message);
    } finally {
      if (token === seq.current) setBusy("");
    }
  };
  /** Show task status and errors for existing API operations. */
  async function run<T>(label: string, action: () => Promise<T>) {
    setBusy(label);
    setError("");
    try {
      return await action();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  }
  /** Parse the structure through the existing RDKit endpoint. */
  async function parseStructure(molblock?: string) {
    const d = await run(tr("RDKit calculation"), () =>
      api<Descriptor>("compounds/describe", {
        name: name || null,
        smiles: smiles || null,
        molblock: molblock || null,
      }),
    );
    if (d) {
      setDescriptor(d);
      setSmiles(d.smiles);
    }
  }
  /** Explicitly resolve shared compound IDs with manual replacement control. */
  async function resolveRetention() {
    const fingerprint = JSON.stringify(current.current);
    const r = await run(tr("Resolving retention"), () =>
      api<{ compounds: Compound[]; records: Record<string, any>[] }>(
        "retention/resolve",
        { method: payload(current.current), overwrite_manual: replaceManual },
      ),
    );
    if (r && fingerprint === JSON.stringify(current.current)) {
      change({
        compounds: r.compounds.map((c) => ({
          ...c,
          descriptors: current.current.compounds.find((x) => x.id === c.id)
            ?.descriptors,
        })),
        workflow: "known",
      });
      setRetentionRecords(r.records);
    } else if (r)
      setError(tr("Inputs changed; retention results were not applied."));
  }
  /** Parse a new compound; the estimation hook fills its initial parameters. */
  async function add() {
    if (current.current.compounds.length >= 20) {
      setError(tr("At most 20 components"));
      return;
    }
    let parsed = descriptor;
    if (smiles) {
      const checked = await run(tr("Parsing compound"), () =>
        api<Descriptor>("compounds/describe", { smiles, name: name || null }),
      );
      if (!checked) return;
      parsed = checked;
    }
    const generated = nextCompoundName(current.current);
    change({
      next_compound_number: name.trim() ? current.current.next_compound_number : generated.next,
      compounds: [
        ...current.current.compounds,
        {
          id: crypto.randomUUID(),
          name: name.trim() || generated.name,
          smiles: parsed?.smiles || smiles || null,
          kind: smiles ? "small_molecule" : "parameterized",
          logkw: null,
          s: null,
          amplitude: 1,
          mixture_parts: 1,
          response_factor: 1,
          parameter_origin: "manual",
          source: "insufficient_data" as const,
          ...(parsed ? { descriptors: parsed } : {}),
        },
      ],
    });
    setName("");
    setSmiles("");
    setDescriptor(undefined);
  }

  /** Mark parameter edits as manual and let structure edits refresh estimated tiers. */
  const editCompound = <K extends keyof Compound>(
    id: string,
    key: K,
    value: Compound[K],
  ) =>
    change({
      compounds: config.compounds.map((c) =>
        c.id === id
          ? {
              ...c,
              [key]: value,
              ...(["logkw", "s"].includes(key)
                ? {
                    parameter_tier: "M" as const,
                    parameter_origin: "manual" as const,
                    source: "model_based" as const,
                    retention_provenance: {
                      features: c.retention_provenance?.features,
                      canonical_smiles:
                        c.retention_provenance?.canonical_smiles,
                      parameter_source: tr("User manual parameters"),
                      source: tr("User manual parameters"),
                      warnings: [
                        tr("Manual parameters; pending user experimental checks"),
                      ],
                    },
                  }
                : {}),
              ...(key === "smiles" && value !== c.smiles
                ? {
                    descriptors: undefined,
                    ...(["M", "D"].includes(compoundTier(c))
                      ? {
                          retention_provenance: {
                            ...c.retention_provenance,
                            features: undefined,
                            canonical_smiles: undefined,
                            warnings: [
                              tr("Structure edited; manual/calibrated parameters retained; molecular descriptors need recalculation."),
                            ],
                          },
                        }
                      : {}),
                  }
                : {}),
              ...(key === "smiles" && c.kind === "parameterized"
                ? { kind: "small_molecule" as const }
                : {}),
            }
          : c,
      ),
    });
  /** Append imported compounds with the existing component limit. */
  async function imported(file: File) {
    const data = new FormData();
    data.set("file", file);
    const rows = await run("Importing", async () => {
      const response = await fetch("/api/compounds/import", {
        method: "POST",
        body: data,
      });
      const d = await response.json();
      if (!response.ok) throw Error(JSON.stringify(d.detail));
      return d.compounds as Compound[];
    });
    if (rows) {
      change({ compounds: [...config.compounds, ...rows].slice(0, 20) });
      if (config.compounds.length + rows.length > 20)
        setError(tr("Import truncated to 20 components"));
    }
  }
  /** Fit the selected compound from supplied method/Rt observations. */
  async function calibrate() {
    let parsed;
    try {
      parsed = calibrationText ? JSON.parse(calibrationText) : observations;
    } catch {
      setError(tr("Invalid observation JSON"));
      return;
    }
    const r = await run(tr("Fitting parameters"), () =>
      api<Record<string, unknown>>("calibrate", {
        compound_id: selected || config.compounds[0]?.id,
        observations: parsed,
      }),
    );
    if (r) setCalibrationResult(r);
  }
  const selectPeak = useCallback((id: string) => setSelected(id), []);
  const header = (
    <>
      <div className="eyebrow">{tr("LIQUID CHROMATOGRAPHY WORKBENCH")}</div>
      <h1>{tabs[tab]}</h1>
      <p className="subtitle">
        {tr("EluSim_V2 — LC Separation Simulation & Gradient Optimization")}</p>
    </>
  );
  return (
    <div className="app">
      <aside>
        <div className="brand">
          <span className="brand-mark">∿</span>EluSim
          <span className="version">V2</span>
        </div>
        <p className="aside-caption">
          {tr("From parameters")}<br />
          {tr("to separation.")}</p>
        <nav aria-label={tr("Workspaces")}>
          {tabs.map((t, i) => (
            <button
              key={t}
              aria-current={tab === i ? "page" : undefined}
              onClick={() => setTab(i)}
            >
              <span>{String(i + 1).padStart(2, "0")}</span>
              {t}
            </button>
          ))}
        </nav>
        <div className="aside-foot">
          {tr("LSS migration engine")}<br />
          {tr("Server-side scientific computing")}</div>
      </aside>
      <main>
        <div className="topbar">
          <span className="status-dot" />
          {health}
          <span className="local-badge">{tr("Private browser workspace")}</span>
        </div>
        <header>
          {header}
          <div className="toolbar">
            <button
              disabled={!!busy || estimates.estimating || !config.compounds.length}
              onClick={() => void simulate()}
            >
              {tr("▶ Run simulation")}</button>
            <label className="check">
              <input
                type="checkbox"
                checked={auto}
                onChange={(e) => setAuto(e.target.checked)}
              />
              {tr("Auto recalculate")}</label>
            <button
              className="secondary"
              onClick={() =>
                download(tr("elusim-project.json"), JSON.stringify(config, null, 2))
              }
            >
              {tr("Save project")}</button>
            <label className="file-button">
              {tr("Load project")}<input
                type="file"
                accept=".json"
                onChange={async (e) => {
                  const f = e.target.files?.[0];
                  if (!f) return;
                  try {
                    const c = migrateProject(JSON.parse(await f.text()));
                    setConfig(c);
                    setStorageError("");
                    setResult(undefined);
                  } catch (x) {
                    setError((x as Error).message);
                  }
                }}
              />
            </label>
          </div>
        </header>
        {storageError && (
          <div role="alert" className="error">
            {storageError} {tr("Saved data was not overwritten. Load a valid project or explicitly reset the demonstration to continue saving.")}</div>
        )}
        {estimates.estimating && (
          <div role="status" className="notice">
            {tr("Estimating retention parameters…")}</div>
        )}
        {busy && (
          <div role="status" className="notice">
            {busy}{tr("… bounded server computation in progress")}</div>
        )}
        {error && (
          <div role="alert" className="error">
            {error}
          </div>
        )}
        <div className="notice soft">
          {tr("RP parameter tiers: A measured curve, B scoped QSRR, C generic C18 estimate, D calibration, M manual. Condition differences are warnings; user experimental checks are pending.")}</div>
        {tab === 0 && (
          <>
            <section>
              <div className="section-head">
                <h2>{tr("Build your mixture")}</h2>
                <button className="secondary" onClick={() => {
                  change({ ...structuredClone(demo), next_compound_number: 1 });
                  setResult(undefined);
                  setSimulationAttempted(false);
                }}>{tr("Load demo mixture")}</button>
                <span>{config.compounds.length} {tr("/ 20 compounds")}</span>
              </div>
              <div className="field-grid">
                <label>
                  {tr("Compound name")}<input
                    aria-label={tr("Compound name")}
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder={tr("Name or local lookup, e.g. caffeine")}
                  />
                </label>
                <label>
                  SMILES
                  <input
                    aria-label="SMILES"
                    value={smiles}
                    onChange={(e) => {
                      setSmiles(e.target.value);
                      setDescriptor(undefined);
                    }}
                    placeholder={tr("Paste a molecular structure")}
                  />
                </label>
              </div>
              <div className="toolbar">
                <button
                  className="secondary"
                  onClick={() => void parseStructure()}
                >
                  {tr("Calculate RDKit descriptors")}</button>
                <button disabled={!!busy} onClick={() => void add()}>
                  {tr("Add compound")}</button>
                <label className="file-button">
                  {tr("Import CSV / SDF / MOL")}<input
                    type="file"
                    accept=".csv,.sdf,.mol"
                    onChange={(e) => {
                      const f = e.target.files?.[0];
                      if (f) void imported(f);
                    }}
                  />
                </label>
              </div>
              {descriptor && (
                <div className="descriptor">
                  <img
                    alt={tr("RDKit molecular structure")}
                    src={
                      "data:image/svg+xml;charset=utf-8," +
                      encodeURIComponent(descriptor.svg)
                    }
                  />
                  <div>
                    <strong>{descriptor.formula}</strong>
                    <p>
                      MW {fmt(descriptor.mw)} · logP {fmt(descriptor.logp)} ·
                      TPSA {fmt(descriptor.tpsa)}
                    </p>
                    <p>
                      HBD {descriptor.hbd} · HBA {descriptor.hba}
                    </p>
                    <p className="muted">{descriptor.prediction_status}</p>
                  </div>
                </div>
              )}
              <StructureEditor
                onParse={(block) => void parseStructure(block)}
              />
            </section>
            <section>
              <h2>{tr("Retention parameters")}</h2>
              <div className="toolbar">
                <button
                  className="secondary"
                  disabled={estimates.estimating}
                  onClick={() => void estimates.estimateAll()}
                >
                  {tr("Re-estimate all A/B/C")}</button>
                <button
                  disabled={estimates.estimating}
                  className="secondary"
                  onClick={() =>
                    download(
                      tr("elusim-parameters.csv"),
                      parameterCsv(config.compounds),
                      "text/csv",
                    )
                  }
                >
                  {tr("Export parameter CSV")}</button>
                <button
                  disabled={!!busy}
                  onClick={() => void resolveRetention()}
                >
                  {tr("Resolve retention from structures")}</button>
                <label className="check">
                  <input
                    type="checkbox"
                    checked={replaceManual}
                    onChange={(e) => setReplaceManual(e.target.checked)}
                  />
                  {tr("Allow replacing manual parameters")}</label>
              </div>
              <p className="muted">
                {tr("Estimates A measured curve → B scoped QSRR → C generic C18 regression. M manual and D calibration values are protected from background changes; method differences remain warnings.")}</p>
              {retentionRecords.map((r, i) => (
                <p className={r.logkw == null ? "warn" : "muted"} key={i}>
                  {config.compounds.find((c) => c.id === r.compound_id)?.name ||
                    r.compound_id}
                  : {tr(r.status)}
                  {r.reason ? " — " + r.reason : ""}
                  {r.condition_mismatches?.length
                    ? " — " + r.condition_mismatches.join("; ")
                    : ""}
                </p>
              ))}
              {retentionRecords.length > 0 && (
                <details>
                  <summary>{tr("Retention resolution results")}</summary>
                  <Metadata value={retentionRecords} />
                </details>
              )}
              <label>
                {tr("Batch relative parts (current displayed order)")}<input
                  aria-label={tr("Batch relative parts")}
                  value={batchParts}
                  onChange={(e) => setBatchParts(e.target.value)}
                  placeholder="5:3:2"
                />
              </label>
              <button
                className="secondary"
                onClick={() => {
                  const values = batchParts.split(/[:,]/).map(Number);
                  if (
                    values.length !== config.compounds.length ||
                    values.some((v) => !Number.isFinite(v) || v < 0) ||
                    values.reduce((s, v) => s + v, 0) <= 0
                  ) {
                    setError(
                      tr("Provide one nonnegative part per current compound and a positive total."),
                    );
                    return;
                  }
                  change({
                    mixture_basis: "parts",
                    compounds: config.compounds.map((c, i) => ({
                      ...c,
                      mixture_parts: values[i],
                    })),
                  });
                }}
              >
                {tr("Apply batch composition")}</button>
              <p>
                {tr("Total parts:")}{" "}
                {config.compounds.reduce(
                  (sum, c) => sum + (c.mixture_parts ?? 1),
                  0,
                )}
              </p>
              <label>
                {tr("Mixture basis")}<select
                  aria-label={tr("Mixture basis")}
                  value={config.mixture_basis || "parts"}
                  onChange={(e) =>
                    change({
                      mixture_basis: e.target.value as
                        | "parts"
                        | "concentration",
                    })
                  }
                >
                  <option value="parts">{tr("Relative parts")}</option>
                  <option value="concentration">{tr("Concentration")}</option>
                </select>
              </label>
              <p className="muted">
                {tr("Up to 20 components · area from injected amount × relative detector response; no calibrated UV absorbance. Legacy amplitude is ignored. All concentrations must use the same unit.")}</p>
              <div className="compound-grid">
                {config.compounds.map((c) => (
                  <article key={c.id}>
                    <div className="section-head">
                      <input
                        aria-label={(tr("Name") + " ") + c.id}
                        value={c.name}
                        onChange={(e) =>
                          editCompound(c.id, "name", e.target.value)
                        }
                      />
                      <SourceBadge compound={c} />
                      <button
                        className="icon"
                        aria-label={(tr("Remove") + " ") + c.name}
                        onClick={() =>
                          change({
                            compounds: config.compounds.filter(
                              (x) => x.id !== c.id,
                            ),
                          })
                        }
                      >
                        ×
                      </button>
                    </div>
                    <div className="field-grid">
                      <Num
                        label={"logKw " + c.name}
                        value={c.logkw}
                        nullable
                        onChange={(v) => editCompound(c.id, "logkw", v)}
                      />
                      <Num
                        label={"S " + c.name}
                        value={c.s}
                        nullable
                        onChange={(v) => editCompound(c.id, "s", v)}
                      />
                      <Num
                        label={(tr("Mixture parts") + " ") + c.name}
                        value={c.mixture_parts ?? 1}
                        onChange={(v) =>
                          editCompound(c.id, "mixture_parts", v ?? 0)
                        }
                      />
                      <span>
                        {(
                          (100 * (c.mixture_parts ?? 1)) /
                          (config.compounds.reduce(
                            (sum, x) => sum + (x.mixture_parts ?? 1),
                            0,
                          ) || 1)
                        ).toFixed(1)}
                        {tr("% relative parts")}</span>
                      <Num
                        label={(tr("Concentration") + " ") + c.name}
                        value={c.concentration ?? null}
                        nullable
                        onChange={(v) => editCompound(c.id, "concentration", v)}
                      />
                      <label>
                        {tr("Concentration unit")}<select
                          value={c.concentration_unit || "mM"}
                          onChange={(e) =>
                            editCompound(
                              c.id,
                              "concentration_unit",
                              e.target.value as Compound["concentration_unit"],
                            )
                          }
                        >
                          <option>mM</option>
                          <option>mg/mL</option>
                        </select>
                      </label>
                      <Num
                        label={(tr("Response factor") + " ") + c.name}
                        value={c.response_factor ?? 1}
                        onChange={(v) =>
                          editCompound(c.id, "response_factor", v ?? 0)
                        }
                      />
                      <label>
                        {tr("Entity type")}<select
                          value={c.kind}
                          onChange={(e) =>
                            editCompound(
                              c.id,
                              "kind",
                              e.target.value as Compound["kind"],
                            )
                          }
                        >
                          {[
                            "small_molecule",
                            "parameterized",
                            "oligomer",
                            "polymer",
                            "peptide",
                            "protein",
                          ].map((x) => (
                            <option key={x} value={x}>{tr(x)}</option>
                          ))}
                        </select>
                      </label>
                    </div>
                    <button
                      className="secondary"
                      disabled={
                        !c.smiles ||
                        c.kind !== "small_molecule" ||
                        compoundTier(c) === "D" ||
                        estimates.estimating
                      }
                      onClick={() => void estimates.estimateOne(c.id, true)}
                    >
                      {tr("Re-estimate")}
                    </button>
                    <label>
                      {tr("Stored SMILES")}<input
                        aria-label={(tr("Stored SMILES") + " ") + c.name}
                        value={c.smiles || ""}
                        onChange={(e) =>
                          editCompound(c.id, "smiles", e.target.value || null)
                        }
                      />
                    </label>
                    {c.source_legacy && (
                      <p className="muted">{tr("Legacy source:")}{tr(c.source_legacy)}</p>
                    )}
                    {c.retention_provenance &&
                      Object.keys(c.retention_provenance).length > 0 && (
                        <details>
                          <summary>{tr("Retention model provenance")}</summary>
                          <Metadata value={c.retention_provenance} />
                        </details>
                      )}
                    {c.scope &&
                      (c.scope.stationary_phase !==
                        config.column.stationary_phase ||
                        c.scope.mobile_a !== config.mobile.a ||
                        c.scope.mobile_b !== config.mobile.b ||
                        c.scope.buffer !== config.mobile.buffer ||
                        c.scope.temperature_c !== config.column.temperature_c ||
                        c.scope.ph !== config.mobile.ph ||
                        (c.scope.ph_control || "fixed") !==
                          (config.mobile.ph_control || "fixed")) && (
                        <p className="warn">
                          {tr("Retention condition differences: simulation uses the supplied parameters with warnings; review or re-estimate for the current method.")}</p>
                      )}
                    <p className="muted">
                      {c.scope
                        ? (tr("Scoped to") + " ") +
                          c.scope.stationary_phase +
                          " / " +
                          c.scope.mobile_b
                        : tr("Parameter scope undeclared; geometry changes retain assumed selectivity.")}
                    </p>
                    <button
                      className="secondary"
                      disabled={
                        c.parameter_origin === "prediction" ||
                        c.parameter_origin === "literature"
                      }
                      onClick={() =>
                        editCompound(c.id, "scope", {
                          stationary_phase: config.column.stationary_phase,
                          mobile_a: config.mobile.a,
                          buffer: config.mobile.buffer,
                          mobile_b: config.mobile.b,
                          ph: config.mobile.ph,
                          ph_control: config.mobile.ph_control || "fixed",
                          temperature_c: config.column.temperature_c,
                        })
                      }
                    >
                      {tr("Bind parameters to current method scope")}</button>
                  </article>
                ))}
              </div>
            </section>
          </>
        )}
        {tab === 1 && (
          <>
            <ModelConditions config={config} change={change} />
            <section>
              <h2>{tr("Independent LC modes")}</h2>
              <div className="mode-grid">
                {["RP", "NP", "HILIC", "IEX", "SEC"].map((m) => (
                  <button
                    className={"mode " + (config.mode === m ? "active" : "")}
                    key={m}
                    onClick={() => change({ mode: m })}
                  >
                    <strong>{m}</strong>
                    <small>
                      {m === "RP"
                        ? tr("Parameter-based LSS")
                        : tr("Quantitative model pending")}
                    </small>
                  </button>
                ))}
              </div>
              {config.mode !== "RP" && (
                <>
                  <div className="notice">
                    {config.mode} {tr("is Unsupported for quantitative simulation. No RP equation is used. Mode-specific parameters may be recorded for future validation.")}</div>
                  <label>
                    {config.mode} {tr("dedicated parameters (JSON)")}<textarea
                      value={modeParams}
                      onChange={(e) => setModeParams(e.target.value)}
                    />
                  </label>
                  <button
                    className="secondary"
                    onClick={() => {
                      try {
                        const params = JSON.parse(modeParams);
                        change({
                          compounds: config.compounds.map((c) => ({
                            ...c,
                            mode_parameters: {
                              ...c.mode_parameters,
                              [config.mode]: params,
                            },
                          })),
                        });
                      } catch {
                        setError(tr("Invalid mode parameter JSON"));
                      }
                    }}
                  >
                    {tr("Save mode parameters")}</button>
                </>
              )}
            </section>
            <section>
              <div className="section-head">
                <h2>{tr("Column geometry & efficiency")}</h2>
                <button
                  className="secondary"
                  onClick={() =>
                    change({
                      column: demo.column,
                      gradient: config.gradient.map((n) => ({
                        ...n,
                        temperature_c: 25,
                      })),
                    })
                  }
                >
                  {tr("Generic C18 template")}</button>
              </div>
              <p className="muted">
                {tr("Generic geometry only. No commercial stationary-phase selectivity database.")}</p>
              <div className="field-grid">
                <label>
                  {tr("Column manufacturer")}<input
                    value={config.column.manufacturer}
                    onChange={(e) =>
                      change({
                        column: {
                          ...config.column,
                          manufacturer: e.target.value,
                        },
                      })
                    }
                  />
                </label>
                <label>
                  {tr("Stationary phase")}<input
                    value={config.column.stationary_phase}
                    onChange={(e) =>
                      change({
                        column: {
                          ...config.column,
                          stationary_phase: e.target.value,
                        },
                      })
                    }
                  />
                </label>
                {(
                  [
                    ["length_mm", tr("Column length (mm)")],
                    ["diameter_mm", tr("Internal diameter (mm)")],
                    ["particle_um", tr("Particle size (µm)")],
                    ["pore_angstrom", tr("Pore size (Å)")],
                    ["porosity", tr("Porosity")],
                    ["void_ml", tr("Void volume (mL, blank = geometry)")],
                    ["plates", tr("Column efficiency (N)")],
                    ["temperature_c", tr("Column temperature (°C)")],
                  ] as const
                ).map(([key, label]) => (
                  <Num
                    key={key}
                    label={label}
                    value={config.column[key]}
                    nullable={key === "void_ml" || key === "plates"}
                    onChange={(v) => {
                      if (key === "temperature_c")
                        change({
                          column: { ...config.column, temperature_c: v! },
                          gradient: config.gradient.map((n) => ({
                            ...n,
                            temperature_c: v!,
                          })),
                        });
                      else change({ column: { ...config.column, [key]: v } });
                    }}
                  />
                ))}
              </div>
            </section>
          </>
        )}
        {tab === 2 && (
          <>
            <section>
              <h2>{tr("Mobile phase & instrument")}</h2>
              <div className="field-grid">
                <label>
                  {tr("Mobile phase A")}<input
                    value={config.mobile.a}
                    onChange={(e) =>
                      change({
                        mobile: { ...config.mobile, a: e.target.value },
                      })
                    }
                  />
                </label>
                <label>
                  {tr("Mobile phase B")}<select
                    value={config.mobile.b}
                    onChange={(e) =>
                      change({
                        mobile: {
                          ...config.mobile,
                          b: e.target.value as "ACN" | "MeOH",
                        },
                      })
                    }
                  >
                    <option>ACN</option>
                    <option>MeOH</option>
                  </select>
                </label>
                <label>
                  {tr("pH condition")}<select
                    value={config.mobile.ph_control || "fixed"}
                    onChange={(e) =>
                      change({
                        mobile: {
                          ...config.mobile,
                          ph_control: e.target.value as "fixed" | "formulation",
                          ph: e.target.value === "formulation" ? null : 7,
                        },
                      })
                    }
                  >
                    <option value="fixed">{tr("Fixed numeric pH")}</option>
                    <option value="formulation">
                      {tr("Formulation-defined, no fixed pH")}</option>
                  </select>
                </label>
                <label>
                  {tr("Buffer")}<input
                    value={config.mobile.buffer}
                    onChange={(e) =>
                      change({
                        mobile: { ...config.mobile, buffer: e.target.value },
                      })
                    }
                  />
                </label>
                {(
                  [
                    ["ph", "pH"],
                    ["injection_ul", tr("Injection volume (µL)")],
                    ["dwell_ml", tr("Dwell volume (mL)")],
                    ["extra_sigma_min", tr("Extra-column sigma (min)")],
                  ] as const
                ).map(([key, label]) => (
                  <Num
                    key={key}
                    label={label}
                    value={config.mobile[key]}
                    disabled={
                      key === "ph" && config.mobile.ph_control === "formulation"
                    }
                    onChange={(v) =>
                      change({ mobile: { ...config.mobile, [key]: v } })
                    }
                  />
                ))}
              </div>
              <p className="muted">
                {tr("pH, temperature and solvent changes refresh A/B/C estimates and warnings. No pKa, ionization or solvent correction is applied.")}</p>
            </section>
            <section>
              <div className="section-head">
                <h2>{tr("Gradient program")}</h2>
                <div className="toolbar">
                  <button
                    className="secondary"
                    onClick={() =>
                      change({
                        gradient: [
                          { ...config.gradient[0], b_percent: 30 },
                          {
                            ...config.gradient[0],
                            time_min: 30,
                            b_percent: 30,
                          },
                        ],
                      })
                    }
                  >
                    {tr("Isocratic")}
                  </button>
                  <button
                    className="secondary"
                    onClick={() =>
                      change({
                        gradient: demo.gradient.map((n) => ({
                          ...n,
                          temperature_c: config.column.temperature_c,
                        })),
                      })
                    }
                  >
                    {tr("Linear + hold")}</button>
                  <button
                    className="secondary"
                    onClick={() => {
                      const n = config.gradient.at(-1)!;
                      change({
                        gradient: [
                          ...config.gradient,
                          {
                            ...n,
                            time_min: n.time_min + 3,
                            b_percent: config.gradient[0].b_percent,
                          },
                          {
                            ...n,
                            time_min: n.time_min + 6,
                            b_percent: config.gradient[0].b_percent,
                          },
                        ],
                      });
                    }}
                  >
                    {tr("Re-equilibrate")}
                  </button>
                </div>
              </div>
              <div className="gradient-list">
                {config.gradient.map((n, i) => (
                  <div className="gradient-row" key={i}>
                    <span className="node-number">{i + 1}</span>
                    {(
                      [
                        ["time_min", tr("Time (min)")],
                        ["b_percent", tr("B (%)", config.mobile.b)],
                        ["flow_ml_min", tr("Flow (mL/min)")],
                        ["temperature_c", tr("Temperature (°C)")],
                      ] as const
                    ).map(([key, label]) => (
                      <Num
                        key={key}
                        label={label + " " + tr("node") + " " + (i + 1)}
                        value={n[key]}
                        onChange={(v) =>
                          change({
                            gradient: config.gradient.map((x, j) =>
                              j === i ? { ...x, [key]: v } : x,
                            ),
                          })
                        }
                      />
                    ))}
                    <label>
                      {tr("Segment")}
                      <select
                        aria-label={tr("Segment") + " " + (i + 1)}
                        value={n.interpolation}
                        onChange={(e) =>
                          change({
                            gradient: config.gradient.map((x, j) =>
                              j === i
                                ? {
                                    ...x,
                                    interpolation: e.target.value as
                                      | "linear"
                                      | "step",
                                  }
                                : x,
                            ),
                          })
                        }
                      >
                        <option value="linear">{tr("Linear / hold")}</option>
                        <option value="step">{tr("Step at next node")}</option>
                      </select>
                    </label>
                    <button
                      className="icon"
                      disabled={i === 0 || config.gradient.length <= 2}
                      aria-label={(tr("Delete node") + " ") + (i + 1)}
                      onClick={() =>
                        change({
                          gradient: config.gradient.filter((_, j) => j !== i),
                        })
                      }
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
              <button
                className="secondary"
                onClick={() => {
                  const n = config.gradient.at(-1)!;
                  change({
                    gradient: [
                      ...config.gradient,
                      { ...n, time_min: n.time_min + 3 },
                    ],
                  });
                }}
              >
                {tr("+ Add gradient node")}</button>
              <p className="muted">
                {tr("Flow interpolates between nodes. Temperature-dependent retention is not enabled; node temperatures must equal the column temperature. Initial composition fills the column before injection.")}</p>
            </section>
          </>
        )}
        {tab === 3 && (
          <>
            {!config.compounds.length && <p>{tr("empty_compounds")}</p>}
            {result && resultKey === configKey ? (
              <>
                <section>
                  <div className="section-head">
                    <h2>{tr("Simulated Chromatogram")}</h2>
                    <label className="check">
                      <input
                        type="checkbox"
                        checked={overlay}
                        onChange={(e) => setOverlay(e.target.checked)}
                      />
                      {tr("Overlay previous run")}</label>
                  </div>
                  {result.traces.some((t) => t.y.some((y) => y > 0)) &&
                  result.peaks.some((p) => p.rt_min != null) ? (
                    <Chart
                      result={result}
                      previous={overlay ? previous : undefined}
                      onSelect={selectPeak}
                    />
                  ) : (
                    <div className="error" data-testid="simulation-incomplete">
                      <h3>
                        {result.peaks.length > 0 &&
                        result.peaks.every(
                          (p) => p.simulation_status === "non_eluted",
                        )
                          ? tr("non_eluted_window")
                          : tr("incomplete_simulation")}
                      </h3>
                      <p>
                        {result.peaks.some((p) => p.rt_min != null)
                          ? tr("Rt 已計算；缺少有效效率或訊號參數，無法產生色譜峰。")
                          : tr("未顯示任何虛構峰。未洗脫表示已完成遷移計算但尚未到達柱出口，並非程式故障。")}
                      </p>
                      {result.peaks.map((p) => (
                        <p key={p.id}>
                          {p.name}: {p.warning || tr("No valid peak")}
                        </p>
                      ))}
                    </div>
                  )}
                  <p className="muted">
                    {tr("Gaussian efficiency approximation · Select a peak for details ·")}{result.model}
                  </p>
                  <div className="toolbar">
                    <button
                      className="secondary"
                      onClick={() =>
                        download(
                          tr("elusim-simulation.json"),
                          JSON.stringify(
                            { input: result.input, result },
                            null,
                            2,
                          ),
                        )
                      }
                    >
                      {tr("Export JSON")}</button>
                    <button
                      className="secondary"
                      onClick={() =>
                        download(
                          tr("elusim-peak-table.csv"),
                          peakTableCsv(result),
                          "text/csv",
                        )
                      }
                    >
                      {tr("Export peak table CSV")}</button>
                    <button
                      className="secondary"
                      onClick={() =>
                        download(
                          tr("elusim-peaks.csv"),
                          "name,rt_min,fwhm_min,width_base_min,source,mixture_fraction,injected_amount,amount_unit,relative_peak_area,relative_peak_height\n" +
                            result.peaks
                              .map((p) =>
                                [
                                  JSON.stringify(p.name),
                                  p.rt_min ?? "",
                                  p.fwhm_min ?? "",
                                  p.width_base_min ?? "",
                                  p.source,
                                  p.mixture_fraction,
                                  p.injected_amount,
                                  p.amount_unit,
                                  p.peak_area,
                                  p.peak_height ?? "",
                                ].join(","),
                              )
                              .join("\n"),
                          "text/csv",
                        )
                      }
                    >
                      {tr("Export peaks CSV")}</button>
                    <button
                      className="secondary"
                      onClick={() =>
                        download(
                          tr("elusim-traces.csv"),
                          "time_min," +
                            result.traces
                              .map((t) => JSON.stringify(t.name))
                              .join(",") +
                            "\n" +
                            result.time_min
                              .map((t, i) =>
                                [t, ...result.traces.map((x) => x.y[i])].join(
                                  ",",
                                ),
                              )
                              .join("\n"),
                          "text/csv",
                        )
                      }
                    >
                      {tr("Export traces CSV")}</button>
                  </div>
                </section>
                <div className="metrics">
                  <div>
                    <span>{tr("Minimum Rs")}</span>
                    <strong>{fmt(result.min_rs)}</strong>
                  </div>
                  <div>
                    <span>{tr("Hold-up time")}</span>
                    <strong>
                      {fmt(result.initial_t0_min)} <small>min</small>
                    </strong>
                  </div>
                  <div>
                    <span>{tr("Solvent volume")}</span>
                    <strong>
                      {fmt(result.total_solvent_ml)} <small>mL</small>
                    </strong>
                  </div>
                  <div>
                    <span>{tr("Eluted components")}</span>
                    <strong>
                      {result.order.length} / {result.peaks.length}
                    </strong>
                  </div>
                </div>
                <section>
                  <GradientProfile result={result} />
                </section>
                <section>
                  <h2>{tr("Elution order & peak metrics")}</h2>
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>{tr("Compound")}</th>
                          <th>{tr("Tier")}</th>
                          <th>{tr("Rt min")}</th>
                          <th>{tr("FWHM min")}</th>
                          <th>{tr("Base width min")}</th>
                          <th>{tr("Relative area / height")}</th>
                          <th>{tr("Source / status")}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {[...result.peaks]
                          .sort(
                            (a, b) =>
                              (a.rt_min ?? Infinity) - (b.rt_min ?? Infinity),
                          )
                          .map((p) => (
                            <tr
                              className={selected === p.id ? "selected" : ""}
                              key={p.id}
                              onClick={() => setSelected(p.id)}
                            >
                              <td>{p.name}</td>
                              <td>
                                <span className="pill" title={p.warning || ""}>
                                  {tierLabel(p.parameter_tier)}
                                </span>
                              </td>
                              <td>{fmt(p.rt_min)}</td>
                              <td>{fmt(p.fwhm_min)}</td>
                              <td>{fmt(p.width_base_min)}</td>
                              <td>
                                {fmt(p.peak_area)} / {fmt(p.peak_height)}
                                <small> · {tr(p.amount_unit)}</small>
                              </td>
                              <td>
                                {sourceLabel(p.source)}
                                {p.warning && (
                                  <p className="warn">{p.warning}</p>
                                )}
                              </td>
                            </tr>
                          ))}
                      </tbody>
                    </table>
                  </div>
                  {result.pairs.map((p) => (
                    <p
                      key={p.ids.join("-")}
                      className={p.coelution ? "warn" : "muted"}
                    >
                      {p.names.join(" ↔ ")} · Rs {fmt(p.rs)}{" "}
                      {p.coelution ? tr("· Co-elution warning") : ""}
                    </p>
                  ))}
                </section>
                <section>
                  <h2>{tr("Model assumptions & scope")}</h2>
                  {[
                    ...result.assumptions,
                    ...result.warnings,
                    result.uncertainty.reason,
                    result.pressure.reason,
                  ].map((s, i) => (
                    <p className="muted" key={i}>
                      {s}
                    </p>
                  ))}
                </section>
              </>
            ) : (
              <section className="empty">
                <h2>
                  {simulationAttempted
                    ? tr("incomplete_simulation")
                    : tr("Ready to simulate")}
                </h2>
                <p>
                  {error ||
                    (result
                      ? tr("stale_results")
                      : busy
                        ? tr("Scientific calculation in progress.")
                        : tr("Supply logKw / S, column geometry and a gradient. Calculations run in the Python backend."))}
                </p>
                {config.compounds
                  .filter((c) => c.logkw == null || c.s == null)
                  .map((c) => (
                    <p className="warn" key={c.id}>
                      {c.name}{tr(": Missing logKw / S. Resolve compatible retention data or calibrate.")}</p>
                  ))}
                <button onClick={() => void simulate()}>{tr("Run simulation")}</button>
              </section>
            )}
          </>
        )}
        {tab === 4 && (
          <OptimizationWorkspace
            config={config}
            apply={(nodes) => {
              setPrevious(result);
              queuedSimulation.current = true;
              change({ gradient: nodes });
              setResult(undefined);
              setTab(3);
            }}
          />
        )}
        {tab === 5 && (
          <>
            <section>
              <h2>{tr("Calibrate from experimental methods")}</h2>
              <p className="muted">
                {tr("At least two independent methods for two parameters. Same phase / solvent / pH / temperature. Fit RMSE is not external accuracy.")}</p>
              <label>
                {tr("Calibration compound")}<select
                  aria-label={tr("Calibration compound")}
                  value={selected || config.compounds[0]?.id}
                  onChange={(e) => setSelected(e.target.value)}
                >
                  {config.compounds.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </label>
              <div className="toolbar">
                <button
                  className="secondary"
                  onClick={() => {
                    const value = prompt(
                      tr("Measured Rt (min) for current method"),
                    );
                    if (value && Number(value) > 0)
                      setObservations([
                        ...observations,
                        { method: payload(config), rt_min: Number(value) },
                      ]);
                  }}
                >
                  {tr("Add measured Rt for current method")}</button>
                <span>{observations.length} {tr("recorded methods")}</span>
                <button
                  className="secondary"
                  onClick={() =>
                    download(
                      tr("elusim-observations.json"),
                      JSON.stringify(observations, null, 2),
                    )
                  }
                >
                  {tr("Export observations")}</button>
                <label className="file-button">
                  {tr("Import observation JSON")}<input
                    type="file"
                    accept=".json"
                    onChange={async (e) => {
                      const f = e.target.files?.[0];
                      if (f) setCalibrationText(await f.text());
                    }}
                  />
                </label>
              </div>
              <label>
                {tr("Observation JSON (optional override)")}<textarea
                  aria-label={tr("Calibration observation JSON")}
                  value={calibrationText}
                  onChange={(e) => setCalibrationText(e.target.value)}
                  placeholder='[{"method": {...}, "rt_min": 6.2}, ...]'
                />
              </label>
              <button disabled={!!busy} onClick={() => void calibrate()}>
                {tr("Fit logKw and S")}</button>
              {calibrationResult && (
                <>
                  <Metadata value={calibrationResult} />
                  <button
                    onClick={() => {
                      const r = calibrationResult;
                      const id = r.compound_id as string;
                      change({
                        compounds: config.compounds.map((c) =>
                          c.id === id
                            ? {
                                ...c,
                                logkw: r.logkw as number,
                                s: r.s as number,
                                source: "calibrated" as const,
                                parameter_tier: "D",
                                parameter_origin: "calibration",
                                retention_provenance: {
                                  model: r.model,
                                  source: tr("User experimental calibration"),
                                  parameter_source:
                                    tr("User experimental calibration"),
                                  model_version: r.model,
                                  features: c.retention_provenance?.features,
                                  canonical_smiles:
                                    c.retention_provenance?.canonical_smiles,
                                  validation_status:
                                    "unvalidated — pending user validation",
                                },
                                scope: r.scope as Scope,
                              }
                            : c,
                        ),
                      });
                    }}
                  >
                    {tr("Apply calibrated parameters")}</button>
                </>
              )}
            </section>
          </>
        )}
        {tab === 6 && (
          <>
            <section>
              <h2>{tr("Model library")}</h2>
              <div className="model-card">
                <div>
                  <h3>{tr("RP · LSS local migration")}</h3>
                  <p>log₁₀ k = logKw − Sφ</p>
                  <p className="muted">
                    {tr("Independent SciPy ODE; plug-flow composition with column and dwell transport. External experimental accuracy is not quantified.")}</p>
                </div>
                <span className="pill ok">{tr("Parameter-based")}</span>
              </div>
              <p>
                {tr("PyLSS fixed reference:")}{" "}
                <code>d2cda850fa0b0881fc3cf1cd68c4d93b59dac04f</code>{tr(". NLSS disabled. CADET license unresolved; not shipped.")}</p>
              <p>
                {tr("Scoped experimental Rt and UV models are available in Retention Prediction and UV-Vis / DAD. TIMPANI / DeepLC pretrained weights are not loaded.")}</p>
              <p>{tr("report0259_info")}</p>
              <h3>{tr("Mode-specific parameter requirements")}</h3>
              <p>{tr("NP: adsorption, competition, water activity.")}</p>
              <p>{tr("HILIC: partition, adsorption and ionic contributions.")}</p>
              <p>{tr("IEX: capacity, ν, σ, rates and salt.")}</p>
              <p>{tr("SEC: pore accessibility, hydrodynamic size and partition.")}</p>
            </section>
            <section>
              <h2>{tr("Licensing & corresponding source")}</h2>
              <p>
                {tr("EluSim_V2 application: AGPL-3.0-or-later. Retention curve data and derived weights: CC BY-NC-SA 3.0 US; non-commercial service only, credited to Boswell and the Wiczling curation team. Scientific parameters supplied by users; browser-local projects are not shared with other visitors.")}</p>
              <div className="toolbar">
                <a className="file-button" href="/api/source">
                  {tr("Download deployed corresponding source")}</a>
                <a className="file-button" href="/api/license">
                  {tr("License")}</a>
              </div>
            </section>
          </>
        )}
        {tab === 7 && <RetentionWorkspace config={config} change={change} />}
        {tab === 8 && <UVWorkspace compounds={config.compounds} />}
        <footer>
          {tr("EluSim · Model-based simulation requires scoped parameters. No model is a substitute for experimental method validation.")}<button
            className="text-button"
            onClick={() => {
              setConfig(emptyProject());
              setStorageError("");
              setResult(undefined);
              setError("");
              setSimulationAttempted(false);
            }}
          >
            {tr("Reset synthetic demonstration")}</button>
        </footer>
      </main>
    </div>
  );
}
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

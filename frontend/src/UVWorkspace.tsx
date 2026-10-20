import { Metadata } from "./Metadata";
import { t as tr } from "./i18n/zh-TW";
import { useEffect, useRef, useState } from "react";
import * as echarts from "echarts";
import type { Compound } from "./types";
type Spectrum = {
  name: string;
  status: string;
  unit: string;
  wavelength_nm: number[];
  intensity: number[];
  original_csv?: string;
  raw?: unknown;
};
function save(name: string, text: string, type: string) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([text], { type }));
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}
export function UVWorkspace({ compounds }: { compounds: Compound[] }) {
  const [smiles, setSmiles] = useState("c1ccccc1"),
    [name, setName] = useState(tr("Spectrum")),
    [solvent, setSolvent] = useState(""),
    [ph, setPh] = useState(""),
    [start, setStart] = useState(190),
    [end, setEnd] = useState(800),
    [resolution, setResolution] = useState(1),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [result, setResult] = useState<any>(),
    [spectra, setSpectra] = useState<Spectrum[]>(() => {
      try {
        return JSON.parse(localStorage.getItem("elusim-uv-spectra") || "[]");
      } catch {
        return [];
      }
    }),
    [unit, setUnit] = useState("absorbance");
  const ref = useRef<HTMLDivElement>(null),
    chart = useRef<echarts.ECharts | null>(null),
    sequence = useRef(0);
  useEffect(() => {
    sequence.current++;
    setBusy(false);
    setResult(undefined);
  }, [smiles, solvent, ph, start, end, resolution]);
  useEffect(() => {
    localStorage.setItem("elusim-uv-spectra", JSON.stringify(spectra));
  }, [spectra]);
  useEffect(() => {
    const c = echarts.init(ref.current!);
    chart.current = c;
    const units = [...new Set(spectra.map((s) => s.unit))];
    c.setOption({
      animation: false,
      legend: { type: "scroll", top: 0 },
      tooltip: { trigger: "axis" },
      grid: { left: 60, right: 60, top: 70, bottom: 80 },
      xAxis: {
        type: "value",
        min: start,
        max: end,
        name: tr("Wavelength (nm)"),
        nameLocation: "middle",
        nameGap: 30,
      },
      yAxis: (units.length
        ? units
        : ["normalized relative absorption (dimensionless)"]
      ).map((u, i) => ({
        type: "value",
        name:
          u === "absorbance"
            ? tr("Absorbance")
            : u.includes("molar")
              ? "ε (L mol⁻¹ cm⁻¹)"
              : tr("Relative absorption"),
        position: i % 2 ? "right" : "left",
        offset: i > 1 ? 45 : 0,
      })),
      dataZoom: [{ type: "inside" }, { type: "slider", bottom: 10 }],
      series: spectra.map((s) => ({
        name: s.name + " · " + tr(s.status),
        type: "line",
        showSymbol: false,
        yAxisIndex: units.indexOf(s.unit),
        data: s.wavelength_nm.map((x, i) => [x, s.intensity[i]]),
        markPoint:
          s.status === "Experimental model prediction" &&
          s.wavelength_nm.includes((s.raw as any)?.lambda_max_nm)
            ? {
                symbol: "circle",
                symbolSize: 8,
                label: { formatter: "λmax", position: "top" },
                data: [
                  {
                    name: tr("Predicted window maximum"),
                    coord: [
                      (s.raw as any).lambda_max_nm,
                      s.intensity[
                        s.wavelength_nm.indexOf((s.raw as any).lambda_max_nm)
                      ],
                    ],
                  },
                ],
              }
            : undefined,
      })),
    });
    const o = new ResizeObserver(() => c.resize());
    o.observe(ref.current!);
    return () => {
      o.disconnect();
      c.dispose();
    };
  }, [spectra, start, end]);
  async function predict() {
    const token = ++sequence.current;
    setBusy(true);
    setError("");
    try {
      const response = await fetch("/api/uv/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          smiles,
          solvent: solvent || null,
          ph: ph === "" ? null : Number(ph),
          start_nm: start,
          end_nm: end,
          resolution_nm: resolution,
        }),
      });
      const r = await response.json();
      if (!response.ok) throw Error(JSON.stringify(r.detail));
      if (token === sequence.current) {
        setResult(r);
        if (r.spectrum)
          setSpectra((old) =>
            [
              ...old,
              {
                name: name + " " + old.length,
                status: r.status,
                unit: r.intensity_unit,
                ...r.spectrum,
                raw: r,
              },
            ].slice(-20),
          );
      }
    } catch (e) {
      if (token === sequence.current) setError(String(e));
    } finally {
      if (token === sequence.current) setBusy(false);
    }
  }
  async function imported(file: File) {
    if (file.size > 180000) {
      setError(tr("Spectrum CSV limit: 180 kB"));
      return;
    }
    try {
      const content = await file.text();
      const response = await fetch("/api/uv/import", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content, name: file.name, unit }),
      });
      const r = await response.json();
      if (!response.ok) throw Error(JSON.stringify(r.detail));
      setSpectra((old) => [...old, r].slice(-20));
    } catch (e) {
      setError(String(e));
    }
  }
  return (
    <>
      <section>
        <h2>{tr("Independent UV-Vis / DAD spectra")}</h2>
        <p>
          {tr(
            "Level 1 chromophore screening · Level 3 experimental full-shape regression, 220–400 nm only. No LC peak-height coupling.",
          )}
        </p>
        <div className="field-grid">
          <label>
            {tr("Spectrum name")}
            <input value={name} onChange={(e) => setName(e.target.value)} />
          </label>
          <label>
            {tr("UV SMILES")}
            <input
              aria-label={tr("UV SMILES")}
              value={smiles}
              onChange={(e) => {
                sequence.current++;
                setBusy(false);
                setSmiles(e.target.value);
                setResult(undefined);
              }}
            />
          </label>
          <label>
            {tr("Mixture compound")}
            <select
              value=""
              onChange={(e) => {
                sequence.current++;
                setBusy(false);
                setSmiles(e.target.value);
                setResult(undefined);
              }}
            >
              <option value="">{tr("Select structure")}</option>
              {compounds
                .filter((c) => c.smiles)
                .map((c) => (
                  <option key={c.id} value={c.smiles!}>
                    {c.name}
                  </option>
                ))}
            </select>
          </label>
          <label>
            {tr("Solvent (blank: dataset-specific)")}
            <input
              aria-label={tr("UV solvent")}
              value={solvent}
              onChange={(e) => setSolvent(e.target.value)}
            />
          </label>
          <label>
            {tr("pH (blank: unconditioned)")}
            <input
              type="number"
              value={ph}
              onChange={(e) => setPh(e.target.value)}
            />
          </label>
          <label>
            {tr("View start (nm)")}
            <input
              type="number"
              aria-label={tr("UV start nm")}
              value={start}
              onChange={(e) => setStart(Number(e.target.value))}
            />
          </label>
          <label>
            {tr("View end (nm)")}
            <input
              type="number"
              aria-label={tr("UV end nm")}
              value={end}
              onChange={(e) => setEnd(Number(e.target.value))}
            />
          </label>
          <label>
            {tr("Sampling step (nm)")}
            <input
              type="number"
              value={resolution}
              onChange={(e) => setResolution(Number(e.target.value))}
            />
          </label>
        </div>
        <button disabled={busy || !smiles} onClick={() => void predict()}>
          {busy ? tr("Predicting…") : tr("Analyze UV structure")}
        </button>
        <p className="warn">
          {tr(
            "Default view 190–800nm; model values exist only at 220–400nm. Solvent/pH adjustments and molar absorptivity are unsupported. No peaks are fabricated for missing or out-of-domain predictions.",
          )}
        </p>
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        {result && (
          <>
            <h3 data-testid="uv-status">{tr(result.status)}</h3>
            <img
              className="molecular-preview"
              alt={tr("UV molecular structure")}
              src={
                "data:image/svg+xml;charset=utf-8," +
                encodeURIComponent(result.structure_svg)
              }
            />
            <p>
              {tr("Matched chromophores:")}
              {Object.entries(result.chromophores)
                .map(([k, v]) => tr(k) + ": " + v)
                .join(", ") || tr("None matched")}
            </p>
            <p>
              {tr("Predicted maximum within 220–400nm:")}
              {result.lambda_max_nm ?? tr("Withheld")}{" "}
              {result.lambda_max_nm ? "nm" : ""}
            </p>
            {result.warnings.map((w: string) => (
              <p key={w} className="muted">
                {w}
              </p>
            ))}
            <details>
              <summary>
                {tr("Descriptors, model evidence & applicability")}
              </summary>
              <Metadata value={result} />
            </details>
          </>
        )}
      </section>
      <section>
        <h2>{tr("Wavelength scan & multiple-spectrum comparison")}</h2>
        <div className="chart" ref={ref} data-testid="uv-chart" />
        <p className="muted">
          {tr(
            "Tap legend / zoom. Unit groups have separate axes; relative shape is not quantitatively comparable to absorbance or ε. Experimental originals are retained. Maximum markers are shown in the result above.",
          )}
        </p>
        <div className="toolbar">
          <button
            className="secondary"
            onClick={() => {
              const a = document.createElement("a");
              a.href = chart.current!.getDataURL({
                type: "png",
                pixelRatio: 2,
                backgroundColor: "#fff",
              });
              a.download = tr("EluSim-UV.png");
              a.click();
            }}
          >
            {tr("Export UV PNG")}
          </button>
          <button
            className="secondary"
            onClick={() => {
              const c = echarts.init(document.createElement("div"), undefined, {
                renderer: "svg",
                width: 1000,
                height: 600,
              });
              c.setOption(chart.current!.getOption());
              save(tr("EluSim-UV.svg"), c.renderToSVGString(), "image/svg+xml");
              c.dispose();
            }}
          >
            {tr("Export UV SVG")}
          </button>
          <button
            className="secondary"
            onClick={() =>
              save(
                tr("EluSim-UV.csv"),
                "name,status,unit,wavelength_nm,intensity\n" +
                  spectra
                    .flatMap((s) =>
                      s.wavelength_nm.map((x, i) =>
                        [
                          JSON.stringify(s.name),
                          JSON.stringify(s.status),
                          JSON.stringify(s.unit),
                          x,
                          s.intensity[i],
                        ].join(","),
                      ),
                    )
                    .join("\n"),
                "text/csv",
              )
            }
          >
            {tr("Export UV CSV")}
          </button>
          <button
            className="secondary"
            onClick={() =>
              save(
                tr("EluSim-UV-originals.json"),
                JSON.stringify(spectra, null, 2),
                "application/json",
              )
            }
          >
            {tr("Export original data JSON")}
          </button>
          <button className="secondary" onClick={() => setSpectra([])}>
            {tr("Clear comparison")}
          </button>
        </div>
        <div className="field-grid">
          <label>
            {tr("Experimental intensity unit")}
            <select value={unit} onChange={(e) => setUnit(e.target.value)}>
              <option value="absorbance">{tr("absorbance")}</option>
              <option value="normalized relative absorption (dimensionless)">
                {tr("normalized relative absorption (dimensionless)")}
              </option>
              <option value="molar absorptivity (L mol^-1 cm^-1)">
                {tr("molar absorptivity (L mol^-1 cm^-1)")}
              </option>
            </select>
          </label>
          <label className="file-button">
            {tr("Import experimental UV CSV")}
            <input
              aria-label={tr("Import UV CSV")}
              type="file"
              accept=".csv"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) void imported(f);
              }}
            />
          </label>
        </div>
        <p>
          {tr(
            "CSV columns: wavelength_nm,intensity. Raw values, unit and original CSV are preserved; importing never retrains or overwrites a model.",
          )}
        </p>
        <ul>
          {spectra.map((s, i) => (
            <li key={i}>
              {s.name} · {tr(s.status)} · {s.intensity.length} {tr("points ·")}
              {tr(s.unit)}
            </li>
          ))}
        </ul>
      </section>
    </>
  );
}

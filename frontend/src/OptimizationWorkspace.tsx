import { fieldHelp, tierLabel, t as tr } from "./i18n/zh-TW";
import { useEffect, useRef, useState } from "react";
import * as echarts from "echarts";
import { api } from "./api";
import { payload, type Config, type Node } from "./types";
import { compoundTier } from "./retentionEstimates";

type Axis = { min: number; max: number; steps: number };
type Candidate = {
  max_pressure_bar?: number | null;
  pressure_feasible?: boolean;
  gradient: Node[];
  min_rs: number | null;
  run_time_min: number | null;
  critical_pair: string[] | null;
  all_eluted: boolean;
  feasible: boolean;
  peaks: { id: string; rt_min: number | null; sigma_min: number | null }[];
  ode_check?: { max_rel_rt: number | null; max_rel_sigma: number | null };
};
type Cube<T> = (T | null)[][][];
type ResolutionMap = {
  axes: {
    gradient_time_min: number[];
    start_percent: number[];
    end_percent: number[];
  };
  min_rs: Cube<number>;
  run_time: Cube<number>;
  all_eluted: Cube<boolean>;
  feasible?: Cube<boolean>;
  critical_pair: Cube<string[]>;
  top_candidates: Candidate[];
  pareto: Candidate[];
  evaluated: number;
  elapsed_s: number;
  warnings: string[];
};
type MultiResult = Candidate & {
  iterations: number;
  evaluations: number;
  time_budget_stopped: boolean;
  warnings: string[];
  search_note: string;
};

/** Download a browser-local search export. */
function save(name: string, content: string, type = "text/csv") {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** Escape CSV fields independently of compound names and IDs. */
function csv(rows: unknown[][]) {
  return rows
    .map((row) =>
      row
        .map((value) => '"' + String(value ?? "").replaceAll('"', '""') + '"')
        .join(","),
    )
    .join("\r\n");
}

/** Format a calculation without presenting a statistical interpretation. */
function number(value: number | null | undefined) {
  return value == null ? "—" : value.toPrecision(5);
}

/** Render one numeric search setting. */
function Numeric({
  label,
  value,
  change,
  integer = false,
}: {
  label: string;
  value: number;
  change: (value: number) => void;
  integer?: boolean;
}) {
  return (
    <label>
      {label}
      <input
        aria-label={label}
        type="number"
        step={integer ? 1 : "any"}
        value={value}
        onChange={(event) => change(Number(event.target.value))}
      />
      {fieldHelp(label) && <small className="muted">{fieldHelp(label)}</small>}
    </label>
  );
}

/** Render an inclusive axis editor. */
function Range({
  label,
  value,
  change,
}: {
  label: string;
  value: Axis;
  change: (value: Axis) => void;
}) {
  return (
    <fieldset>
      <legend>{label}</legend>
      <div className="field-grid">
        {(["min", "max", "steps"] as const).map((key) => (
          <Numeric
            key={key}
            label={label + "：" + tr(key)}
            value={value[key]}
            integer={key === "steps"}
            change={(next) => change({ ...value, [key]: next })}
          />
        ))}
      </div>
    </fieldset>
  );
}

/** Render one ECharts surface and dispose event handlers on unmount. */
function SearchPlot({
  option,
  label,
  onPoint,
}: {
  option: echarts.EChartsOption;
  label: string;
  onPoint: (index: number) => void;
}) {
  const element = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const chart = echarts.init(element.current!);
    chart.setOption(option);
    chart.on("click", (event) => onPoint(event.dataIndex));
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(element.current!);
    return () => {
      observer.disconnect();
      chart.dispose();
    };
  }, [option, onPoint]);
  return (
    <div className="search-plot-scroll">
      <div
        ref={element}
        role="img"
        aria-label={tr(label)}
        data-testid={label}
        style={{ minWidth: 620, height: 380 }}
      />
    </div>
  );
}

/** Search the shared method without restricting ranges by source tier. */
export function OptimizationWorkspace({
  config,
  apply,
}: {
  config: Config;
  apply: (nodes: Node[]) => void;
}) {
  const [duration, setDuration] = useState<Axis>({
    min: 2,
    max: 60,
    steps: 30,
  });
  const [start, setStart] = useState<Axis>({ min: 0, max: 50, steps: 11 });
  const [end, setEnd] = useState<Axis>({ min: 30, max: 100, steps: 15 });
  const [initialHold, setInitialHold] = useState(0);
  const [finalHold, setFinalHold] = useState(3);
  const [target, setTarget] = useState(1.5);
  const [maximum, setMaximum] = useState("");
  const [segments, setSegments] = useState(2);
  const [budget, setBudget] = useState(20);
  const [minSegment, setMinSegment] = useState(0.5);
  const [map, setMap] = useState<ResolutionMap>();
  const [multi, setMulti] = useState<MultiResult>();
  const [slice, setSlice] = useState(0);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [elapsed, setElapsed] = useState(0);
  const controller = useRef<AbortController | null>(null);
  const sequence = useRef(0);
  const fingerprint = JSON.stringify({
    method: payload(config),
    duration,
    start,
    end,
    initialHold,
    finalHold,
    target,
    segments,
    budget,
    minSegment,
    maximum,
  });

  useEffect(() => {
    sequence.current++;
    controller.current?.abort();
    setMap(undefined);
    setMulti(undefined);
    setBusy("");
    return () => controller.current?.abort();
  }, [fingerprint]);

  useEffect(() => {
    if (!busy) return;
    const started = Date.now();
    const timer = setInterval(
      () => setElapsed((Date.now() - started) / 1000),
      200,
    );
    return () => clearInterval(timer);
  }, [busy]);

  /** Submit a bounded search; stale or cancelled responses cannot replace results. */
  async function search(kind: "map" | "multisegment") {
    controller.current?.abort();
    const request = new AbortController();
    controller.current = request;
    const token = ++sequence.current;
    setBusy(
      kind === "map"
        ? tr("Computing resolution map")
        : tr("Searching multi-segment gradient"),
    );
    setElapsed(0);
    setError("");
    if (kind === "map") {
      setMap(undefined);
      setMulti(undefined);
    } else setMulti(undefined);
    const common = {
      simulation: payload(config),
      initial_hold_min: initialHold,
      final_hold_min: finalHold,
      target_rs: target,
      max_run_time_min: maximum === "" ? null : Number(maximum),
    };
    try {
      if (kind === "map") {
        const response = await api<ResolutionMap>(
          "optimize/map",
          {
            ...common,
            gradient_time_min: duration,
            start_percent: start,
            end_percent: end,
          },
          request.signal,
        );
        if (token === sequence.current) {
          setMap(response);
          setSlice(0);
        }
      } else {
        const response = await api<MultiResult>(
          "optimize/multisegment",
          {
            ...common,
            segments,
            start_percent_bounds: [start.min, start.max],
            end_percent_bounds: [end.min, end.max],
            total_gradient_time_bounds: [duration.min, duration.max],
            seed: 42,
            time_budget_s: budget,
            min_segment_min: minSegment,
            initial_candidate: map?.top_candidates[0]?.gradient ?? null,
          },
          request.signal,
        );
        if (token === sequence.current) setMulti(response);
      }
    } catch (caught) {
      if (token === sequence.current && (caught as Error).name !== "AbortError")
        setError((caught as Error).message);
    } finally {
      if (token === sequence.current) setBusy("");
    }
  }

  /** Abort the HTTP operation; server-side disconnect handling stops its worker. */
  function cancel() {
    sequence.current++;
    controller.current?.abort();
    setBusy("");
    setError(tr("Search cancelled"));
  }

  /** Require explicit permission before replacing the current method. */
  function confirmApply(nodes: Node[]) {
    if (window.confirm(tr("Replace the current gradient and run simulation?")))
      apply(nodes);
  }

  /** Describe the critical pair with current compound IDs and source tiers. */
  function pairLabel(ids: string[] | null) {
    if (!ids) return "—";
    const compounds = ids.map((id) =>
      config.compounds.find((compound) => compound.id === id),
    );
    return (
      compounds.map((compound) => compound?.name ?? "?").join(" / ") +
      (compounds.some((compound) => compound && compoundTier(compound) === "C")
        ? " · " + tr("includes_estimates")
        : "")
    );
  }

  /** Reconstruct the clicked cell using the same holds, flow and temperature. */
  function applyCell(endIndex: number, timeIndex: number) {
    if (!map || map.all_eluted[slice][endIndex][timeIndex] == null) return;
    const startPercent = map.axes.start_percent[slice];
    const endPercent = map.axes.end_percent[endIndex];
    const durationMin = map.axes.gradient_time_min[timeIndex];
    const node = (time_min: number, b_percent: number): Node => ({
      time_min,
      b_percent,
      flow_ml_min: config.gradient[0].flow_ml_min,
      temperature_c: config.column.temperature_c,
      interpolation: "linear",
    });
    const nodes = [node(0, startPercent)];
    if (initialHold) nodes.push(node(initialHold, startPercent));
    nodes.push(node(initialHold + durationMin, endPercent));
    if (finalHold)
      nodes.push(node(initialHold + durationMin + finalHold, endPercent));
    confirmApply(nodes);
  }

  /** Export every cell, including null entries for disallowed combinations. */
  function exportMap() {
    if (!map) return;
    const rows: unknown[][] = [
      [
        "start",
        "end",
        "time",
        "min_rs",
        "run_time",
        "all_eluted",
        "critical_pair",
      ],
    ];
    map.axes.start_percent.forEach((startPercent, startIndex) =>
      map.axes.end_percent.forEach((endPercent, endIndex) =>
        map.axes.gradient_time_min.forEach((time, timeIndex) =>
          rows.push([
            startPercent,
            endPercent,
            time,
            map.min_rs[startIndex][endIndex][timeIndex],
            map.run_time[startIndex][endIndex][timeIndex],
            map.all_eluted[startIndex][endIndex][timeIndex],
            map.critical_pair[startIndex][endIndex][timeIndex]?.join("|"),
          ]),
        ),
      ),
    );
    save(tr("resolution-map.csv"), csv(rows));
  }

  /** Export ranked candidate metrics and programmed nodes. */
  function exportCandidates() {
    if (!map) return;
    save(
      tr("gradient-candidates.csv"),
      csv([
        [
          "rank",
          "gradient",
          "min_rs",
          "run_time",
          "critical_pair",
          "max_rel_rt",
          "max_rel_sigma",
        ],
        ...map.top_candidates.map((candidate, index) => [
          index + 1,
          JSON.stringify(candidate.gradient),
          candidate.min_rs,
          candidate.run_time_min,
          candidate.critical_pair?.join("|"),
          candidate.max_pressure_bar,
          candidate.ode_check?.max_rel_rt,
          candidate.ode_check?.max_rel_sigma,
        ]),
      ]),
    );
  }

  const heatCells: {
    value: [number, number, number];
    itemStyle?: { borderColor: string; borderWidth: number };
  }[] = [];
  const heatIndices: [number, number][] = [];
  map?.axes.end_percent.forEach((_, endIndex) =>
    map.axes.gradient_time_min.forEach((_, timeIndex) => {
      const resolution = map.min_rs[slice][endIndex][timeIndex];
      if (resolution == null) return;
      const runtime = map.run_time[slice][endIndex][timeIndex];
      heatIndices.push([endIndex, timeIndex]);
      heatCells.push({
        value: [timeIndex, endIndex, resolution],
        itemStyle:
          resolution >= target &&
          (maximum === "" || (runtime != null && runtime <= Number(maximum)))
            ? { borderColor: "#172e35", borderWidth: 2 }
            : undefined,
      });
    }),
  );
  const heatOption: echarts.EChartsOption = {
    animation: false,
    tooltip: {
      renderMode: "richText",
      formatter: (event: any) => {
        const [endIndex, timeIndex] = heatIndices[event.dataIndex];
        return (
          "Rs " +
          number(map!.min_rs[slice][endIndex][timeIndex]) +
          "\n" +
          tr("Run") +
          " " +
          number(map!.run_time[slice][endIndex][timeIndex]) +
          " min\n" +
          pairLabel(map!.critical_pair[slice][endIndex][timeIndex])
        );
      },
    },
    grid: { left: 80, right: 30, bottom: 100, top: 25 },
    xAxis: {
      type: "category",
      name: tr("Gradient time (min)"),
      nameLocation: "middle",
      nameGap: 30,
      data: map?.axes.gradient_time_min.map((value) => value.toFixed(2)),
    },
    yAxis: {
      type: "category",
      name: tr("End %B", config.mobile.b),
      data: map?.axes.end_percent.map((value) => value.toFixed(1)),
    },
    visualMap: {
      type: "piecewise",
      orient: "horizontal",
      left: "center",
      bottom: 0,
      pieces: [
        { lte: target - 1e-8, color: "#e9b3a3", label: tr("< target Rs") },
        { gte: target, color: "#4ba59b", label: tr("≥ target Rs") },
      ],
    },
    series: [{ type: "heatmap", data: heatCells }],
  };
  const paretoOption: echarts.EChartsOption = {
    animation: false,
    tooltip: {
      trigger: "item",
      renderMode: "richText",
      formatter: (event: any) => {
        const candidate = map?.pareto[event.dataIndex];
        return candidate
          ? tr("Run time (min)") +
              ": " +
              number(candidate.run_time_min) +
              "\n" +
              tr("Minimum Rs") +
              ": " +
              number(candidate.min_rs) +
              "\n" +
              pairLabel(candidate.critical_pair)
          : "";
      },
    },
    grid: { left: 75, right: 30, bottom: 70, top: 30 },
    xAxis: {
      type: "value",
      name: tr("Run time (min)"),
      nameLocation: "middle",
      nameGap: 35,
    },
    yAxis: { type: "value", name: tr("Minimum Rs") },
    series: [
      {
        type: "scatter",
        symbolSize: 14,
        data: map?.pareto.map((candidate) => [
          candidate.run_time_min,
          candidate.min_rs,
        ]),
      },
    ],
  };

  const validAxes = [duration, start, end].every(
    (axis) =>
      Number.isInteger(axis.steps) && axis.steps >= 1 && axis.steps <= 100,
  );
  const combinations = !validAxes
    ? 0
    : Array.from(
        { length: start.steps },
        (_, i) =>
          start.min +
          ((start.max - start.min) * i) / Math.max(1, start.steps - 1),
      ).reduce(
        (count, first) =>
          count +
          Array.from(
            { length: end.steps },
            (_, i) =>
              end.min + ((end.max - end.min) * i) / Math.max(1, end.steps - 1),
          ).filter((last) => last > first + 1).length *
            duration.steps,
        0,
      );
  if (!config.compounds.length)
    return (
      <section>
        <h2>{tr("Gradient Optimization")}</h2>
        <p>{tr("empty_compounds")}</p>
      </section>
    );
  return (
    <section className="optimizer-workspace">
      <h2>{tr("Gradient Optimization")}</h2>
      <p>
        {tr(
          "Constant-flow LSS calculations · user experimental checks pending · search ranges are independent of parameter tier.",
        )}
      </p>
      <p>
        {config.compounds
          .map(
            (compound) =>
              compound.name + "（" + tierLabel(compoundTier(compound)) + "）",
          )
          .join(" · ")}
      </p>
      <div className="field-grid">
        <Range
          label={tr("Gradient time (min)")}
          value={duration}
          change={setDuration}
        />
        <Range
          label={tr("Start %B", config.mobile.b)}
          value={start}
          change={setStart}
        />
        <Range
          label={tr("End %B", config.mobile.b)}
          value={end}
          change={setEnd}
        />
        <Numeric
          label={tr("Initial hold (min)")}
          value={initialHold}
          change={setInitialHold}
        />
        <Numeric
          label={tr("Final hold (min)")}
          value={finalHold}
          change={setFinalHold}
        />
        <Numeric
          label={tr("Target minimum Rs")}
          value={target}
          change={setTarget}
        />
        <label>
          {tr("Maximum analysis time (min)")}
          <input
            type="number"
            aria-label={tr("Maximum analysis time (min)")}
            value={maximum}
            onChange={(event) => setMaximum(event.target.value)}
          />
          <small className="muted">{tr("help_maximum")}</small>
        </label>
      </div>
      <button disabled={!!busy} onClick={() => void search("map")}>
        {tr("Generate resolution map")}
      </button>
      <span data-testid="combination-count">
        {tr("combinations").replace(
          "{count}",
          combinations.toLocaleString("zh-TW"),
        )}
      </span>
      <label>
        {tr("Segments")}
        <select
          aria-label={tr("Segments")}
          value={segments}
          onChange={(event) => setSegments(Number(event.target.value))}
        >
          <option value={2}>2</option>
          <option value={3}>3</option>
        </select>
        <small className="muted">{tr("help_segments")}</small>
      </label>
      <Numeric
        label={tr("Search time budget (s)")}
        value={budget}
        change={setBudget}
      />
      <Numeric
        label={tr("Minimum segment duration (min)")}
        value={minSegment}
        change={setMinSegment}
      />
      <button disabled={!!busy} onClick={() => void search("multisegment")}>
        {tr("Optimize multi-segment gradient")}
      </button>
      {busy && (
        <div role="status">
          {busy} · {elapsed.toFixed(1)} s
          <button onClick={cancel}>{tr("Cancel search")}</button>
        </div>
      )}
      {error && <p role="alert">{error}</p>}
      {map && (
        <>
          <h3>{tr("Resolution map")}</h3>
          <p>
            {map.evaluated} {tr("candidates ·")}
            {map.elapsed_s.toFixed(3)}{" "}
            {tr("s · outlined cells meet the displayed target and time limit")}
          </p>
          <label>
            {tr("Start %B slice:", config.mobile.b)}
            {map.axes.start_percent[slice]}
            <input
              aria-label={tr("Start %B slice", config.mobile.b)}
              type="range"
              min={0}
              max={map.axes.start_percent.length - 1}
              value={slice}
              onChange={(event) => setSlice(Number(event.target.value))}
            />
          </label>
          <SearchPlot
            option={heatOption}
            label="resolution-map"
            onPoint={(index) => applyCell(...heatIndices[index])}
          />
          <details>
            <summary>{tr("Keyboard cell selection")}</summary>
            <div className="search-table-scroll">
              <table>
                <tbody>
                  {map.axes.end_percent.map((endPercent, endIndex) => (
                    <tr key={endIndex}>
                      {map.axes.gradient_time_min.map(
                        (durationMin, timeIndex) => (
                          <td key={timeIndex}>
                            <button
                              disabled={
                                map.all_eluted[slice][endIndex][timeIndex] ==
                                null
                              }
                              aria-label={
                                tr("Apply map cell") +
                                " " +
                                endIndex +
                                " " +
                                timeIndex
                              }
                              onClick={() => applyCell(endIndex, timeIndex)}
                            >
                              {endPercent}% / {durationMin.toFixed(1)} min
                            </button>
                          </td>
                        ),
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
          <button onClick={exportMap}>{tr("Export map CSV")}</button>
          <button onClick={exportCandidates}>
            {tr("Export candidates CSV")}
          </button>
          <h3>{tr("Top candidates")}</h3>
          <div className="search-table-scroll">
            <table data-testid="optimizer-candidates">
              <thead>
                <tr>
                  <th>{tr("Rank / nodes (%B @ min)", config.mobile.b)}</th>
                  <th>{tr("Minimum Rs")}</th>
                  <th>{tr("Run (min)")}</th>
                  <th>{tr("max_pressure")}</th>
                  <th>{tr("Critical pair")}</th>
                  <th>{tr("ODE relative differences (Rt / σ)")}</th>
                  <th>{tr("Apply")}</th>
                </tr>
              </thead>
              <tbody>
                {map.top_candidates.map((candidate, index) => (
                  <tr key={index}>
                    <td>
                      {index + 1}:{" "}
                      {candidate.gradient
                        .map(
                          (node) =>
                            node.b_percent.toFixed(1) +
                            " @ " +
                            node.time_min.toFixed(2),
                        )
                        .join(" → ")}
                    </td>
                    <td>{number(candidate.min_rs)}</td>
                    <td>{number(candidate.run_time_min)}</td>
                    <td>{number(candidate.max_pressure_bar)}</td>
                    <td>{pairLabel(candidate.critical_pair)}</td>
                    <td>
                      {number(candidate.ode_check?.max_rel_rt)} /{" "}
                      {number(candidate.ode_check?.max_rel_sigma)}
                    </td>
                    <td>
                      <button onClick={() => confirmApply(candidate.gradient)}>
                        {tr("Apply candidate")} {index + 1}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <h3>{tr("Pareto frontier")}</h3>
          <SearchPlot
            option={paretoOption}
            label="pareto-map"
            onPoint={(index) => confirmApply(map.pareto[index].gradient)}
          />
          <details>
            <summary>{tr("Keyboard Pareto selection")}</summary>
            {map.pareto.map((candidate, index) => (
              <button
                key={index}
                onClick={() => confirmApply(candidate.gradient)}
              >
                {tr("Apply Pareto")} {index + 1}
              </button>
            ))}
          </details>
          {map.warnings.map((warning) => (
            <p key={warning} className="warning">
              {warning}
            </p>
          ))}
        </>
      )}
      {multi && (
        <section data-testid="multisegment-result">
          <h3>{tr("Multi-segment search result")}</h3>
          <p>{multi.search_note}</p>
            <p>{tr("max_pressure")}：{number(multi.max_pressure_bar)} bar</p>
          <p>
            {tr("Minimum Rs")}
            {number(multi.min_rs)} {tr("· run")}
            {number(multi.run_time_min)} min · {multi.iterations}{" "}
            {tr("iterations ·")}
            {multi.evaluations} {tr("evaluations · budget stop")}
            {tr(String(multi.time_budget_stopped))}
          </p>
          <p>
            {multi.gradient
              .map(
                (node) =>
                  node.b_percent.toFixed(2) +
                  "% @ " +
                  node.time_min.toFixed(3) +
                  " min",
              )
              .join(" → ")}
          </p>
          <p>
            {pairLabel(multi.critical_pair)} {tr("· ODE differences")}{" "}
            {number(multi.ode_check?.max_rel_rt)} /{" "}
            {number(multi.ode_check?.max_rel_sigma)}
          </p>
          {multi.warnings.map((warning) => (
            <p key={warning}>{warning}</p>
          ))}
          <button onClick={() => confirmApply(multi.gradient)}>
            {tr("Apply multi-segment result")}
          </button>
          <button
            onClick={() =>
              save(
                tr("multisegment-result.json"),
                JSON.stringify(multi, null, 2),
                "application/json",
              )
            }
          >
            {tr("Export multi-segment JSON")}
          </button>
        </section>
      )}
      <section>
        <h3>{tr("Across-mode screening")}</h3>
        <p>
          {tr(
            "RP search uses supplied or estimated LSS parameters. NP, HILIC, IEX and SEC require independent parameters and experiments; no quantitative cross-mode ranking is generated.",
          )}
        </p>
      </section>
    </section>
  );
}

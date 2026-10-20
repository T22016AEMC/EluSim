import { t as tr } from "./i18n/zh-TW";
import { useEffect, useState } from "react";
import { api } from "./api";
import type { Config, Scope } from "./types";
export type CurveConditions = {
  model_id: string;
  model_version: string;
  scope: Scope & { mode: string };
  phi_range: [number, number];
  particle_um: number;
  notice: string;
};
export function compatibleMethod(
  config: Config,
  m: CurveConditions,
): Partial<Config> {
  const s = m.scope;
  const flow = config.gradient[0]?.flow_ml_min ?? 0.3;
  return {
    mode: s.mode,
    workflow: "known",
    column: {
      ...config.column,
      stationary_phase: s.stationary_phase,
      particle_um: m.particle_um,
      temperature_c: s.temperature_c,
    },
    mobile: {
      ...config.mobile,
      a: s.mobile_a,
      b: s.mobile_b,
      buffer: s.buffer,
      ph: s.ph,
      ph_control: s.ph_control,
    },
    gradient: [
      {
        time_min: 0,
        b_percent: m.phi_range[0] * 100,
        flow_ml_min: flow,
        temperature_c: s.temperature_c,
        interpolation: "linear",
      },
      {
        time_min: 10,
        b_percent: m.phi_range[1] * 100,
        flow_ml_min: flow,
        temperature_c: s.temperature_c,
        interpolation: "linear",
      },
      {
        time_min: 20,
        b_percent: m.phi_range[1] * 100,
        flow_ml_min: flow,
        temperature_c: s.temperature_c,
        interpolation: "linear",
      },
    ],
  };
}
export function conditionDifferences(c: Config, m: CurveConditions) {
  const actual = {
    mode: c.mode,
    stationary_phase: c.column.stationary_phase,
    mobile_a: c.mobile.a,
    mobile_b: c.mobile.b,
    buffer: c.mobile.buffer,
    ph: c.mobile.ph,
    ph_control: c.mobile.ph_control || "fixed",
    temperature_c: c.column.temperature_c,
  };
  const differences = Object.entries(m.scope)
    .filter(([k, v]) => actual[k as keyof typeof actual] !== v)
    .map(
      ([k, v]) =>
        tr(k) +
        ": " +
        tr(String(actual[k as keyof typeof actual])) +
        (" " + tr("→ required") + " ") +
        tr(String(v)),
    );
  if (c.column.particle_um !== m.particle_um)
    differences.push(
      tr("particle_um") +
        ": " +
        c.column.particle_um +
        (" " + tr("→ required") + " ") +
        m.particle_um,
    );
  c.gradient.forEach((n, i) => {
    if (
      n.b_percent < m.phi_range[0] * 100 ||
      n.b_percent > m.phi_range[1] * 100
    )
      differences.push(
        tr("Gradient node") +
          " " +
          (i + 1) +
          ": " +
          n.b_percent +
          (tr("% B → required", c.mobile.b) + " ") +
          m.phi_range.map((x) => x * 100).join("–") +
          "%",
      );
    if (n.temperature_c !== m.scope.temperature_c)
      differences.push(
        tr("Gradient node") +
          " " +
          (i + 1) +
          (" " + tr("temperature: required") + " ") +
          m.scope.temperature_c +
          "°C",
      );
  });
  return differences;
}
export function ModelConditions({
  config,
  change,
  onLoaded,
}: {
  config: Config;
  change: (c: Partial<Config>) => void;
  onLoaded?: () => void;
}) {
  const [model, setModel] = useState<CurveConditions>(),
    [error, setError] = useState("");
  useEffect(() => {
    api<CurveConditions>("retention/conditions")
      .then(setModel)
      .catch((e) => setError(String(e)));
  }, []);
  return (
    <div className="notice soft">
      <strong>{tr("Model-compatible LC conditions")}</strong>
      <p>
        {tr(
          "Explicitly apply the existing measured-curve / experimental QSRR scope. This replaces column chemistry, mobile phase and gradient settings; geometry and efficiency stay user supplied. It does not validate QSRR accuracy.",
        )}
      </p>
      {model && (
        <>
          <p>
            {model.model_id} / {model.model_version} ·{" "}
            {model.scope.stationary_phase} · {model.scope.temperature_c}°C ·{" "}
            {model.phi_range.map((x) => x * 100).join("–")}
            {tr("% B", config.mobile.b)}
          </p>
          <ul>
            {conditionDifferences(config, model).map((x) => (
              <li key={x}>{x}</li>
            ))}
          </ul>
          {conditionDifferences(config, model).length === 0 && (
            <p>{tr("Current method matches the model conditions.")}</p>
          )}
          <button
            className="secondary"
            onClick={() => {
              change(compatibleMethod(config, model));
              onLoaded?.();
            }}
          >
            {tr("Use model-compatible conditions")}
          </button>
        </>
      )}
      {error && <p role="alert">{error}</p>}
    </div>
  );
}

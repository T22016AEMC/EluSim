import { t } from "./i18n/zh-TW";
import type { Config } from "./types";

type Props = { config: Config; change: (update: Partial<Config>) => void };

/** Edit a reference input with its own unit and explanation. */
function ReferenceNumber({ label, help, value, change, nullable = false }: {
  label: string;
  help: string;
  value: number | null;
  change: (value: number | null) => void;
  nullable?: boolean;
}) {
  return <label>
    {t(label)}
    <input type="number" step="any" aria-label={t(label)} value={value ?? ""}
      onChange={(event) => change(nullable && event.target.value === ""
        ? null : Number(event.target.value))} />
    <small>{t(help)}</small>
  </label>;
}

/** Edit optional column efficiency inputs without replacing fixed-N behavior. */
export function ColumnPhysics({ config, change }: Props) {
  const column = config.column;
  const dynamic = column.efficiency_model === "van_deemter";
  return <section>
    <h2>{t("column_physics")}</h2>
    <p className="muted">{t("reference_pending")}</p>
    <div className="field-grid">
      <label>{t("efficiency_model")}
        <select aria-label={t("efficiency_model")} value={column.efficiency_model ?? "fixed"}
          onChange={(event) => change({ column: { ...column,
            efficiency_model: event.target.value as "fixed" | "van_deemter" } })}>
          <option value="fixed">{t("fixed_plates")}</option>
          <option value="van_deemter">{t("dynamic_plates")}</option>
        </select>
        <small>{t("efficiency_help")}</small>
      </label>
      {dynamic && <>
        {(["vd_a", "vd_b", "vd_c"] as const).map((key, index) =>
          <ReferenceNumber key={key} label={key} help="knox_help"
            value={column[key] ?? [1, 2, 0.05][index]}
            change={(value) => change({ column: { ...column, [key]: value! } })} />)}
        <ReferenceNumber label="diffusion" help="diffusion_help"
          value={(column.diffusion_m2_s ?? 1e-9) / 1e-9}
          change={(value) => change({ column: { ...column, diffusion_m2_s: value! * 1e-9 } })} />
      </>}
      <ReferenceNumber label="flow_resistance" help="resistance_help"
        value={column.flow_resistance ?? 500}
        change={(value) => change({ column: { ...column, flow_resistance: value! } })} />
    </div>
  </section>;
}

/** Keep mixer delay additional to the separate pure dwell translation. */
export function InstrumentPhysics({ config, change }: Props) {
  return <section>
    <h2>{t("instrument_physics")}</h2>
    <div className="field-grid">
      <ReferenceNumber label="mixer_ml" help="mixer_help"
        value={config.mobile.mixer_ml ?? 0}
        change={(value) => change({ mobile: { ...config.mobile, mixer_ml: value! } })} />
      <ReferenceNumber label="system_pressure" help="system_pressure_help"
        value={config.mobile.system_pressure_bar ?? 0}
        change={(value) => change({ mobile: { ...config.mobile, system_pressure_bar: value! } })} />
    </div>
  </section>;
}

/** A blank upper bound adds no pressure constraint to optimization. */
export function PressureLimit({ config, change }: Props) {
  return <div className="field-grid">
    <ReferenceNumber label="pressure_limit" help="pressure_limit_help"
      nullable value={config.max_pressure_bar ?? null}
      change={(value) => change({ max_pressure_bar: value })} />
  </div>;
}

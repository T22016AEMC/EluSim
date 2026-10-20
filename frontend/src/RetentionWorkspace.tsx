import { CompoundIssue, SourceBadge } from "./SourceBadge";
import { t } from "./i18n/zh-TW";
import type { Config } from "./types";

/** Read the shared compounds without a second model or source selection path. */
export function RetentionWorkspace({
  config,
}: {
  config: Config;
  change?: (config: Partial<Config>) => void;
}) {
  return (
    <section>
      <h2>{t("Retention Prediction")}</h2>
      <p>{t("source_readonly")}</p>
      {!config.compounds.length && <p>{t("empty_compounds")}</p>}
      {config.compounds.map((compound) => (
        <article
          key={compound.id}
          data-testid={"retention-record-" + compound.id}
        >
          <h3>
            {compound.name} <SourceBadge compound={compound} />
          </h3>
          <p>
            logKw: {compound.logkw ?? "—"} · S: {compound.s ?? "—"}
          </p>
          <CompoundIssue compound={compound} config={config} />
          {((compound.retention_provenance?.warnings as string[]) ?? []).map(
            (warning, index) => (
              <p className="warn" key={index}>
                {t(warning)}
              </p>
            ),
          )}
          <p>
            {t("Model version")}:{" "}
            {String(compound.retention_provenance?.model_version ?? "—")}
          </p>
        </article>
      ))}
    </section>
  );
}

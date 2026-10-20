import { t } from "./i18n/zh-TW";

/** Identify the compound and field behind a schema error without changing payloads. */
export function validationMessage(detail: unknown, body?: unknown): string {
  if (!Array.isArray(detail)) {
    return typeof detail === "string" ? t(detail) : JSON.stringify(detail);
  }
  return detail.map((item: any) => {
    const path = (item.loc || []).filter((part: unknown) => part !== "body");
    let node: any = body;
    let compound: any;
    for (let index = 0; index < path.length; index++) {
      node = node?.[path[index]];
      if (path[index - 1] === "compounds") compound = node;
    }
    const prefix = compound ? String(compound.name || compound.id) + " (" + String(compound.id) + ") — " : "";
    return prefix + path.map((part: string) => t(String(part))).join(".") + ": " + t(item.msg);
  }).join("\n");
}

/** Call the existing JSON API and report translated errors with HTTP context. */
export async function api<T>(path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  const response = await fetch("/api/" + path, {
    method: body ? "POST" : "GET",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
    signal,
  });
  let data: any;
  try {
    data = await response.json();
  } catch {
    throw Error(t("api_non_json").replace("{path}", path).replace("{status}", String(response.status)));
  }
  if (!response.ok) {
    throw Error(t("api_error").replace("{path}", path).replace("{status}", String(response.status)) + " — " + validationMessage(data.detail, body));
  }
  return data;
}

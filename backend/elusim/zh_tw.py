"""Localize display messages at the API boundary, preserving inputs and codes."""
import functools
import json
import re
from pathlib import Path


@functools.lru_cache(maxsize=1)
def catalog():
    """Load the generated copy of the frontend presentation dictionary."""
    return json.loads(Path(__file__).with_name("zh_tw.json").read_text(encoding="utf-8"))


def message(value):
    """Translate only display text, including notices with numeric context."""
    if not isinstance(value, str):
        return value
    labels = catalog()
    if value in labels:
        return labels[value]
    translated = value
    for original, replacement in sorted(labels.items(), key=lambda item: -len(item[0])):
        if len(original) > 18 and re.search(r"[A-Za-z]", original):
            translated = translated.replace(original, replacement)
    translated = re.sub(
        r"([a-z_]+): current (.*?); (required|source) ",
        lambda match: f"{labels.get(match[1], match[1])}：目前 {match[2]}；來源條件 ",
        translated,
    )
    translated = re.sub(
        r"gradient\[(\d+)\]\.b_percent: current (.*?); source interval ",
        lambda match: f"梯度節點 {int(match[1]) + 1} 有機溶劑比例：目前 {match[2]}%；來源區間 ",
        translated,
    )
    translated = translated.replace("Value error, ", "")
    return translated


DISPLAY_KEYS = {
    "warning", "warnings", "detail", "msg", "assumptions", "reason", "notice",
    "limitations", "description", "search_note", "prediction_status",
    "parameter_source", "rule", "application_notes", "condition_differences",
    "condition_mismatches", "lss_warning",
}
OPAQUE_KEYS = {
    "input", "input_conditions", "method", "simulation", "scope", "parameter_scope",
    "raw", "original_csv", "structure_svg", "svg", "features", "metadata",
    "model", "models", "training_dataset", "retention_method",
}


def present(value, key=None):
    """Preserve every number and wire identifier while translating display fields."""
    if key in OPAQUE_KEYS:
        return value
    if isinstance(value, dict):
        output = {field: present(item, field) for field, item in value.items()}
        if isinstance(value.get("status"), str):
            output["status_label"] = message(value["status"])
        if isinstance(value.get("tier"), str):
            output["tier_label"] = catalog().get("source_" + value["tier"], value.get("tier_label"))
        return output
    if isinstance(value, list):
        return [present(item, key) for item in value]
    if key in DISPLAY_KEYS:
        return message(value)
    return value

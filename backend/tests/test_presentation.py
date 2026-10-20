"""Program behavior for presentation and legacy workflow compatibility."""
from fastapi.testclient import TestClient

from elusim.estimation import parameter_tier
from elusim.main import app, _rates
from elusim.retention_registry import resolve_compounds
from elusim.schemas import Compound
from elusim.zh_tw import present
from test_engine import method


def test_localization_preserves_wire_codes_and_echoed_inputs():
    """Display localization cannot rewrite machine state or echoed user methods."""
    body = {
        "status": "Insufficient data",
        "source": "unknown_legacy",
        "input": {"mobile": {"a": "Water"}, "compounds": [{"name": "Measured"}]},
        "warnings": ["Missing logKw / S"],
    }
    output = present(body)
    assert output["status"] == body["status"]
    assert output["source"] == body["source"]
    assert output["input"] == body["input"]
    assert output["status_label"] == "資料不足"
    assert output["warnings"] == ["缺少 logKw／S。"]


def test_calibration_and_manual_sources_do_not_enter_background_estimation(monkeypatch):
    """A legacy workflow selector cannot override explicit source precedence."""
    calibrated = Compound(id="cal", name="校正", logkw=2, s=4, smiles="CCO",
                          parameter_origin="calibration", parameter_tier="D")
    manual = Compound(id="manual", name="手動", logkw=2, s=4, smiles="CCO",
                      parameter_origin="manual", parameter_tier="M")
    def unexpected_estimate(*args, **kwargs):
        raise AssertionError("Protected parameters entered background estimation")
    monkeypatch.setattr("elusim.estimation.estimate_retention", unexpected_estimate)
    request = method().model_copy(update={"workflow": "calibrated", "compounds": [calibrated, manual]})
    resolved, records = resolve_compounds(request)
    assert [parameter_tier(compound) for compound in resolved.compounds] == ["D", "M"]
    assert [compound.source for compound in resolved.compounds] == ["calibrated", "model_based"]
    assert resolved.workflow == "known"
    assert all("preserved" in record["status"] for record in records)


def test_api_translates_error_text_without_changing_http_status():
    """A parsing error keeps its status while providing a Chinese explanation."""
    _rates.clear()
    with TestClient(app) as client:
        response = client.post("/api/compounds/describe", json={"smiles": "not a molecule"})
    assert response.status_code == 422
    assert "結構無效" in response.json()["detail"]


def test_backend_catalog_matches_the_frontend_source():
    """Prevent API/UI message drift without reading any scientific dataset."""
    import json
    from pathlib import Path
    from elusim.zh_tw import catalog

    root = Path(__file__).resolve().parents[2]
    source = (root / "frontend/src/i18n/zh-TW.ts").read_text(encoding="utf-8-sig")
    start = source.index("{", source.index("export const zhTW"))
    end = source.index("\n};", start) + 2
    assert catalog() == json.loads(source[start:end])

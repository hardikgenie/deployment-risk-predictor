from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "SYNTHETIC" in response.json()["data_type"]


def test_predict_has_expected_shape_and_notice():
    response = client.post("/predict", json={
        "changed_files": 12,
        "lines_added": 350,
        "lines_deleted": 100,
        "test_failure_count": 0,
        "test_pass_rate": 98.0,
        "code_quality_issues": 3,
        "security_findings": 0,
        "pipeline_retries": 0,
        "recent_deploy_failures": 0,
        "config_change": 0,
        "dependency_change": 0,
    })
    assert response.status_code == 200
    data = response.json()
    assert 0 <= data["risk_probability"] <= 1
    assert 0 <= data["risk_percent"] <= 100
    assert data["risk_category"] in {"LOW", "MEDIUM", "HIGH"}
    assert "synthetic" in data["data_notice"].lower()


def test_invalid_feature_is_rejected():
    response = client.post("/predict", json={"changed_files": -1})
    assert response.status_code == 422

from app import main as app_main


def sample_ci_report():
    return {
        "schema_version": 1,
        "run": {
            "repository": "hardikgenie/deployment-risk-predictor",
            "workflow": "CI - Deployment Risk Analysis",
            "run_id": "12345",
            "run_attempt": 1,
            "event": "push",
            "ref": "refs/heads/main",
            "commit_sha": "0123456789abcdef",
            "run_url": "https://github.com/hardikgenie/deployment-risk-predictor/actions/runs/12345",
        },
        "pipeline": {
            "tests": {"tests": 8, "failures": 0, "errors": 0, "skipped": 0, "pass_rate_percent": 100.0, "workflow_outcome": "success", "report_available": True},
            "static_analysis": {"tool": "Ruff", "outcome": "success", "finding_count": 0, "report_available": True},
            "dependency_security": {"tool": "pip-audit", "outcome": "success", "vulnerability_count": 0, "report_available": True},
            "container_build": {"outcome": "success"},
        },
        "change_signals": {"changed_files": 3, "lines_added": 40, "lines_deleted": 12, "diff_measured": True, "config_change": False, "dependency_change": False},
        "features_sent_to_demo_model": {"changed_files": 3, "test_pass_rate": 100},
        "feature_sources_measured": {"change_diff": True, "test_junit": True, "ruff_findings": True, "dependency_audit": True, "deployment_history": False},
        "model_output": {"type": "RandomForestClassifier", "training_data": "SYNTHETIC_DEMO", "demo_score_percent": 21.2, "demo_category": "LOW", "validated_for_research": False},
        "decision": {"advisory_status": "MANDATORY_CHECKS_PASSED_DEMO_SCORE_ADVISORY", "explanation": "Demo only.", "production_deployment": "NOT_PERFORMED", "risk_score_controls_mandatory_gates": False},
        "warnings": ["Synthetic data only.", "Deployment history is not measured."],
    }


def test_ci_latest_explains_when_no_report_is_available(monkeypatch, tmp_path):
    monkeypatch.setattr(app_main, "PUBLIC_CI_REPORT_URL", None)
    monkeypatch.setattr(app_main, "IMPORTED_CI_REPORT_PATH", tmp_path / "imported.json")
    monkeypatch.setattr(app_main, "GENERATED_CI_REPORT_PATH", tmp_path / "generated.json")
    response = client.get("/api/ci/latest")
    assert response.status_code == 200
    assert response.json()["available"] is False
    assert "download" in response.json()["message"].lower()


def test_dashboard_can_import_and_render_pipeline_report(monkeypatch, tmp_path):
    monkeypatch.setattr(app_main, "PUBLIC_CI_REPORT_URL", None)
    monkeypatch.setattr(app_main, "IMPORTED_CI_REPORT_PATH", tmp_path / "imported.json")
    monkeypatch.setattr(app_main, "GENERATED_CI_REPORT_PATH", tmp_path / "generated.json")
    response = client.post("/api/ci/import", json=sample_ci_report())
    assert response.status_code == 200
    assert response.json()["available"] is True

    latest = client.get("/api/ci/latest")
    assert latest.status_code == 200
    payload = latest.json()
    assert payload["available"] is True
    assert payload["source"] == "imported_github_actions_artifact"
    assert payload["report"]["pipeline"]["container_build"]["outcome"] == "success"
    assert payload["report"]["model_output"]["validated_for_research"] is False


def test_ci_import_rejects_unrecognised_payload():
    response = client.post("/api/ci/import", json={"hello": "world"})
    assert response.status_code == 422


def test_ci_latest_reads_published_github_feed(monkeypatch):
    class FakeResponse:
        status_code = 200
        def json(self):
            return sample_ci_report()

    monkeypatch.setattr(app_main, "PUBLIC_CI_REPORT_URL", "https://raw.githubusercontent.com/example/repo/ci-reports/latest-ci-risk-report.json")
    monkeypatch.setattr(app_main.httpx, "get", lambda *args, **kwargs: FakeResponse())
    response = client.get("/api/ci/latest")
    assert response.status_code == 200
    assert response.json()["available"] is True
    assert response.json()["source"] == "github_actions_latest_report"


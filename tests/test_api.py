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


def test_launch_control_dashboard_is_available_and_discloses_demo_scope():
    response = client.get("/launch-control")
    assert response.status_code == 200
    assert "Launch Control" in response.text
    assert "SIMULATED DEMO" in response.text
    assert "No GitLab API is contacted" in response.text

"""Minimal API/UI prototype for predictive deployment risk analysis.

Important: the included model is a synthetic-data demonstration only. It is not
validated for production decisions or for dissertation conclusions.
"""
from pathlib import Path
import json
import joblib
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from scripts.train_demo_model import train_and_save

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "artifacts" / "demo_model.joblib"
META_PATH = ROOT / "artifacts" / "demo_model_metadata.json"
STATIC_PATH = ROOT / "static"

if not MODEL_PATH.exists():
    train_and_save()
_model_bundle = joblib.load(MODEL_PATH)
_model = _model_bundle["model"]
FEATURES = _model_bundle["features"]
_metadata = json.loads(META_PATH.read_text(encoding="utf-8")) if META_PATH.exists() else {}

app = FastAPI(title="Deployment Risk Predictor", version="0.1.0", description="Research prototype using synthetic demo data.")
app.mount("/static", StaticFiles(directory=str(STATIC_PATH)), name="static")


class DeploymentFeatures(BaseModel):
    changed_files: int = Field(12, ge=0, le=1000)
    lines_added: int = Field(350, ge=0, le=100000)
    lines_deleted: int = Field(100, ge=0, le=100000)
    test_failure_count: int = Field(0, ge=0, le=1000)
    test_pass_rate: float = Field(98.0, ge=0, le=100)
    code_quality_issues: int = Field(3, ge=0, le=10000)
    security_findings: int = Field(0, ge=0, le=1000)
    pipeline_retries: int = Field(0, ge=0, le=1000)
    recent_deploy_failures: int = Field(0, ge=0, le=1000)
    config_change: int = Field(0, ge=0, le=1)
    dependency_change: int = Field(0, ge=0, le=1)


@app.get("/", response_class=HTMLResponse)
def index():
    html_path = STATIC_PATH / "index.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.get("/health")
def health():
    return {"status": "ok", "model_type": "RandomForestClassifier", "data_type": _metadata.get("data_type", "unknown")}


def explain_drivers(f: DeploymentFeatures):
    drivers = []
    if f.test_failure_count > 0: drivers.append("Test failures are present")
    if f.test_pass_rate < 90: drivers.append("Test pass rate is below 90%")
    if f.security_findings > 0: drivers.append("Security findings are present")
    if f.recent_deploy_failures > 0: drivers.append("Recent deployment failures are reported")
    if f.config_change: drivers.append("Configuration change is flagged")
    if f.dependency_change: drivers.append("Dependency change is flagged")
    if f.changed_files > 30: drivers.append("Large number of changed files")
    if f.code_quality_issues > 10: drivers.append("Elevated static-analysis findings")
    if f.pipeline_retries > 2: drivers.append("Multiple pipeline retries")
    if not drivers: drivers.append("No obvious high-severity flags in the entered demo features")
    return drivers[:4]


@app.post("/predict")
def predict(features: DeploymentFeatures):
    try:
        row = np.array([[getattr(features, name) for name in FEATURES]], dtype=float)
        probability = float(_model.predict_proba(row)[0][1])
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Prediction failed. Check the local model artifact.") from exc
    category = "HIGH" if probability >= 0.67 else "MEDIUM" if probability >= 0.34 else "LOW"
    return {
        "risk_probability": round(probability, 4),
        "risk_percent": round(probability * 100, 1),
        "risk_category": category,
        "drivers": explain_drivers(features),
        "data_notice": "Synthetic-data demo model only. Do not use this output for production release decisions or as a dissertation finding.",
    }

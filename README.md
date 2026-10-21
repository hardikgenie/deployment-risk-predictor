# AI-Driven CI/CD Deployment Risk Analysis — Starter Prototype

This repository is an initial, runnable proof-of-concept for the BITS Pilani M.Tech dissertation **“Design and Development of an AI-Driven Intelligent CI/CD Pipeline for Predictive Deployment Risk Analysis.”** It contains a small API/UI, a demonstration Random Forest model, API tests, a Dockerfile, and GitHub Actions CI.

## Important academic-integrity note

**The included training data and model are synthetic and illustrative only.** The labels are generated from a toy rule so the application is runnable before real data exists. Do not report its score, evaluation metrics, or UI examples as research findings. Do not use it for production release decisions. Before dissertation experiments, collect/construct and document valid CI/CD observations, define outcome labels, prevent feature leakage, then train and evaluate on that dataset.

## Requirements

- Python 3.10+ (workflow tested on Python 3.11)
- VS Code recommended

## Run locally in VS Code

Open this folder in VS Code, then in the integrated terminal:

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python scripts/train_demo_model.py
uvicorn app.main:app --reload
```

### Windows PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python scripts/train_demo_model.py
uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000>. API health check: <http://127.0.0.1:8000/health>. API docs: <http://127.0.0.1:8000/docs>.

The first page shows 11 pre-deployment signal inputs and returns a demo risk score, category, and heuristic review prompts. The page clearly labels the model as synthetic demo data. It also includes a **CI pipeline evidence** panel; this panel displays the latest locally generated CI report or a GitHub Actions report imported through the UI.

## Show GitHub Actions pipeline results in the dashboard

After the enhanced `.github/workflows/ci.yml` workflow completes on a push or manual dispatch, the workflow publishes the generated `ci-risk-report.json` to the dedicated `ci-reports` branch. The local dashboard's **CI pipeline evidence** panel checks this public raw-JSON feed when you open or refresh the page; it then displays run metadata, changed files and line counts, tests, Ruff findings, pip-audit vulnerabilities, Docker build status, demo score, and measurement warnings. Pull-request runs do not publish to that branch.

For the automatic feed to work, the repository must be public and the workflow needs `contents: write` permission to update the dedicated report branch. No separate repository secret is needed; the workflow uses the short-lived `GITHUB_TOKEN`. The `ci-reports` branch holds only the generated report JSON. If the feed is unavailable (for example, before the first successful report-publishing run, while offline, or for a private repository), you can use the UI's **Import workflow report JSON** control: download and unzip the `ci-risk-evidence` artifact from Actions, then select `artifacts/ci-risk-report.json`. Imported JSON is saved locally as `artifacts/dashboard_latest_ci_report.json` and ignored by Git.

**Research integrity:** the model score remains based on synthetic demonstration data. CI stage outcomes and scan findings are actual pipeline evidence; the demo score is not a validated deployment-failure probability and must not be presented as dissertation findings.

## Run tests

```bash
pytest -q
```

The GitHub Actions workflow `.github/workflows/ci.yml` runs on pushes and pull requests to `main`/`master`, installs dependencies, rebuilds the synthetic demo model, runs the tests, and builds the Docker image as a container smoke check.

## Run with Docker

```bash
docker build -t deployment-risk-predictor .
docker run --rm -p 8000:8000 deployment-risk-predictor
```

Then open <http://127.0.0.1:8000>.

## Add to your GitHub project

Recommended: create a **dedicated repository for the dissertation prototype** and put this project at the repository root. If you instead place the app in a subfolder of another repository, GitHub Actions will not discover a workflow nested inside that subfolder: copy `.github/workflows/ci.yml` to the repository-root `.github/workflows/` and update paths / `working-directory` values accordingly. Avoid putting dissertation code into an unrelated class-project repository. If you are creating a new repository:

```bash
git init
git add .
git commit -m "Add deployment risk prediction prototype"
git branch -M main
git remote add origin https://github.com/<YOUR-USERNAME>/<YOUR-REPOSITORY>.git
git push -u origin main
```

Replace the repository URL placeholder with the real repo URL. This package does not push to GitHub on your behalf. GitHub stores the source and runs the CI workflow; it does **not** host this FastAPI app as a running web service. Public hosting requires a runtime such as Azure Container Apps / AKS or another container host, plus deployment configuration and credentials.

## Current prototype flow

1. CI/CD features are entered into the demo form.
2. The FastAPI service validates the request.
3. A Random Forest artifact returns a synthetic-demo risk probability.
4. A risk band and heuristic prompts are displayed.
5. GitHub Actions smoke-tests the API and request validation.

## Next research implementation steps

1. Capture real or controlled CI/CD runs with timestamps and reproducible execution IDs.
2. Define an outcome label (e.g., failed deployment, rollback, or a pre-agreed failure criterion) separately from the prediction-time features.
3. Build a tabular dataset with one row per pipeline execution and document the inclusion/exclusion rules.
4. Split data without leakage (prefer time-aware or grouped splitting when runs are related).
5. Compare a simple baseline (e.g., Logistic Regression) with Random Forest / XGBoost; report suitable precision/recall/F1 and ROC-AUC/PR-AUC rather than accuracy alone.
6. Integrate the validated model as a decision-support step before deployment promotion; keep existing quality/security gates and human review.

## Repository layout

```text
app/main.py                       FastAPI app and prediction endpoint
static/index.html                 local dashboard UI
scripts/train_demo_model.py       synthetic demo dataset + model training
artifacts/                         generated demo model/metadata
tests/test_api.py                  API smoke tests
.github/workflows/ci.yml          GitHub Actions CI
Dockerfile                         container build/run
```

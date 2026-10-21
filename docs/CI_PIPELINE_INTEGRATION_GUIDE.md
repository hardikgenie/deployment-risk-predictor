# CI pipeline risk-evidence integration

This add-on integrates a **synthetic-model advisory stage** into GitHub Actions. It is intentionally not a production deployment gate. The useful engineering outcome at this stage is that a real GitHub Actions run produces a traceable evidence report containing code-change counts, pytest results, Ruff findings, dependency-audit findings, Docker build outcome, the demonstration model output, known missing telemetry, and limitations.

## Install into your existing local repository

From the root of `deployment-risk-predictor`, extract this add-on ZIP over the existing tree, or copy these files while preserving your `.git` folder:

- `.github/workflows/ci.yml` (replaces the existing simple workflow)
- `scripts/ci_risk_assessment.py` (new)
- `tests/test_ci_risk_assessment.py` (new)
- `docs/CI_PIPELINE_INTEGRATION_GUIDE.md` (new)

No access tokens or repository secrets are required for this read-only workflow.

## Run locally

```bash
pip install -r requirements.txt
python -m pip install 'ruff>=0.6,<1.0' 'pip-audit>=2.7,<3.0'
mkdir -p artifacts
python scripts/train_demo_model.py
pytest -q --junitxml=artifacts/pytest.xml
ruff check app scripts tests --output-format=json > artifacts/ruff-report.json || true
pip-audit -r requirements.txt --format=json > artifacts/pip-audit.json || true
docker build -t deployment-risk-predictor:local .
TEST_OUTCOME=success RUFF_OUTCOME=success SECURITY_OUTCOME=success DOCKER_OUTCOME=success \
  python scripts/ci_risk_assessment.py --junitxml artifacts/pytest.xml \
  --ruff-report artifacts/ruff-report.json --audit-report artifacts/pip-audit.json
```

For the local command above, set the environment variables to the **actual outcomes** of the commands you ran; do not write `success` if that command failed. If you skip Docker or a security scan, mark the relevant outcome `not_run`.

## See the evidence after pushing

1. Push this change to `main` (or open a pull request against `main`).
2. Open the repository's **Actions** tab.
3. Open the latest `CI - Deployment Risk Analysis` run.
4. Read the job Summary for the evidence table and advisory output.
5. Download the `ci-risk-evidence` artifact to inspect JSON, Markdown, JUnit, Ruff, and dependency-audit reports.

## What is collected

- Change-size signals: changed-path count, lines added/deleted, configuration-change flag, dependency-change flag.
- Validation: pytest JUnit results and pass rate.
- Static analysis: Ruff findings.
- Dependency security: pip-audit vulnerability count/report status.
- Build: Docker build outcome.
- Traceability: repository, event, ref, commit and run URL where available.

`recent_deploy_failures` is not connected to deployment history yet and is explicitly marked unmeasured. Pipeline retry count is approximated from GitHub run attempt. Any uncollected feature is called out in the report; a zero in the demo feature vector must not be interpreted as evidence that no real-world findings exist.

## Policy and academic integrity

- Tests and Docker build remain authoritative mandatory CI checks.
- The synthetic ML score never fails or approves a production deployment.
- The workflow does not deploy to production.
- The score and metrics from the synthetic model must not be reported as dissertation findings.
- For the research experiment, replace the synthetic trainer with a documented dataset from controlled or observed runs, define outcome labels, use leakage-safe splits, compare baseline models and evaluate on held-out data.

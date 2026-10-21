"""Create an evidence report for a GitHub Actions run.

This deliberately uses the project's synthetic demo model so the end-to-end CI
integration can be exercised before research data exists. Its score is NOT a
validated deployment-failure probability and never overrides mandatory gates.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "artifacts" / "demo_model.joblib"
META_PATH = ROOT / "artifacts" / "demo_model_metadata.json"

FEATURE_DEFAULTS: dict[str, float] = {
    "changed_files": 0,
    "lines_added": 0,
    "lines_deleted": 0,
    "test_failure_count": 0,
    "test_pass_rate": 100,
    "code_quality_issues": 0,
    "security_findings": 0,
    "pipeline_retries": 0,
    "recent_deploy_failures": 0,
    "config_change": 0,
    "dependency_change": 0,
}


def run_git(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, text=True, capture_output=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def load_event() -> dict[str, Any]:
    event_path = os.getenv("GITHUB_EVENT_PATH")
    if event_path and Path(event_path).is_file():
        try:
            return json.loads(Path(event_path).read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def changed_files_and_diff(event: dict[str, Any]) -> tuple[list[str], int, int, bool]:
    """Return changed paths, insertions, deletions, and whether diff was measured."""
    base = head = ""
    if event.get("pull_request"):
        pr = event["pull_request"]
        base = str((pr.get("base") or {}).get("sha", ""))
        head = str((pr.get("head") or {}).get("sha", ""))
    elif event.get("before") and event.get("after"):
        base, head = str(event.get("before", "")), str(event.get("after", ""))

    numstat = ""
    name_status = ""
    zero_sha = "0" * 40
    if head and base and base != zero_sha:
        numstat = run_git(["diff", "--numstat", base, head])
        name_status = run_git(["diff", "--name-only", base, head])
    elif head:
        numstat = run_git(["diff-tree", "--root", "--no-commit-id", "--numstat", "-r", head])
        name_status = run_git(["diff-tree", "--root", "--no-commit-id", "--name-only", "-r", head])
    else:
        numstat = run_git(["diff", "--numstat", "HEAD~1", "HEAD"])
        name_status = run_git(["diff", "--name-only", "HEAD~1", "HEAD"])
        if not name_status:
            numstat = run_git(["diff-tree", "--root", "--no-commit-id", "--numstat", "-r", "HEAD"])
            name_status = run_git(["diff-tree", "--root", "--no-commit-id", "--name-only", "-r", "HEAD"])

    paths = [p for p in name_status.splitlines() if p.strip()]
    additions = deletions = 0
    measured = bool(numstat or name_status)
    for line in numstat.splitlines():
        parts = line.split("\t", 2)
        if len(parts) < 3:
            continue
        add_raw, del_raw = parts[0], parts[1]
        if add_raw.isdigit():
            additions += int(add_raw)
        if del_raw.isdigit():
            deletions += int(del_raw)
    # Pull-request metadata is a dependable fallback if git diff couldn't be read.
    if not measured and event.get("pull_request"):
        pr = event["pull_request"]
        additions = int(pr.get("additions", 0) or 0)
        deletions = int(pr.get("deletions", 0) or 0)
        count = int(pr.get("changed_files", 0) or 0)
        if count and not paths:
            paths = ["(paths unavailable; counts supplied by pull-request metadata)"] * count
        measured = count > 0 or additions > 0 or deletions > 0
    return paths, additions, deletions, measured


def parse_junit(path: Path, outcome: str) -> dict[str, Any]:
    result = {
        "report_available": path.is_file(),
        "tests": 0,
        "failures": 0,
        "errors": 0,
        "skipped": 0,
        "pass_rate_percent": 100.0 if outcome == "success" else 0.0,
        "outcome": outcome or "unknown",
    }
    if not path.is_file():
        return result
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError):
        result["report_available"] = False
        return result
    suites = [root] if root.tag.endswith("testsuite") else root.findall(".//testsuite")
    for suite in suites:
        result["tests"] += int(suite.attrib.get("tests", 0) or 0)
        result["failures"] += int(suite.attrib.get("failures", 0) or 0)
        result["errors"] += int(suite.attrib.get("errors", 0) or 0)
        result["skipped"] += int(suite.attrib.get("skipped", 0) or 0)
    failed = result["failures"] + result["errors"]
    counted = max(0, result["tests"] - result["skipped"])
    passed = max(0, counted - failed)
    result["pass_rate_percent"] = round(100.0 * passed / counted, 2) if counted else (100.0 if outcome == "success" else 0.0)
    return result


def parse_ruff(path: Path) -> tuple[int, bool]:
    if not path.is_file():
        return 0, False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return (len(payload) if isinstance(payload, list) else 0), isinstance(payload, list)
    except (json.JSONDecodeError, OSError):
        return 0, False


def parse_audit(path: Path) -> tuple[int, bool]:
    if not path.is_file():
        return 0, False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            dependencies = payload
        elif isinstance(payload, dict):
            dependencies = payload.get("dependencies", [])
        else:
            return 0, False
        count = sum(len(dep.get("vulns", [])) for dep in dependencies if isinstance(dep, dict))
        return count, True
    except (json.JSONDecodeError, OSError):
        return 0, False


def classify_advisory(category: str, tests_outcome: str, docker_outcome: str) -> tuple[str, str]:
    if tests_outcome != "success":
        return "BLOCKED_BY_EXISTING_CI_GATE", "Automated tests did not pass; the mandatory test gate remains authoritative."
    if docker_outcome != "success":
        return "BLOCKED_BY_EXISTING_CI_GATE", "Container build did not pass; the mandatory build gate remains authoritative."
    if category == "HIGH":
        return "REVIEW_ADVISED_DEMO_ONLY", "The synthetic demo model labels this run HIGH; review the evidence, but do not treat the score as validated."
    if category == "MEDIUM":
        return "REVIEW_ADVISED_DEMO_ONLY", "The synthetic demo model labels this run MEDIUM; this is advisory only."
    return "MANDATORY_CHECKS_PASSED_DEMO_SCORE_ADVISORY", "Tests and container build passed; the model score is synthetic and does not approve a production release."


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    event = load_event()
    event_name = os.getenv("GITHUB_EVENT_NAME", "local")
    test_outcome = os.getenv("TEST_OUTCOME", args.tests_outcome or "unknown")
    ruff_outcome = os.getenv("RUFF_OUTCOME", args.ruff_outcome or "unknown")
    security_outcome = os.getenv("SECURITY_OUTCOME", args.security_outcome or "unknown")
    docker_outcome = os.getenv("DOCKER_OUTCOME", args.docker_outcome or "unknown")

    changed_paths, added, deleted, diff_measured = changed_files_and_diff(event)
    junit = parse_junit(args.junitxml, test_outcome)
    quality_count, quality_measured = parse_ruff(args.ruff_report)
    vuln_count, security_measured = parse_audit(args.audit_report)
    config_paths = [p.lower() for p in changed_paths]
    config_change = any(
        "/.github/workflows/" in f"/{p}/" or p.endswith(("dockerfile", ".tf", ".tfvars", ".yaml", ".yml"))
        or p.startswith(("terraform/", "helm/", "k8s/", "kubernetes/"))
        for p in config_paths
    )
    dependency_names = ("requirements.txt", "pyproject.toml", "poetry.lock", "uv.lock", "pipfile", "package-lock.json", "package.json")
    dependency_change = any(any(p.endswith(n) for n in dependency_names) for p in config_paths)
    attempt = int(os.getenv("GITHUB_RUN_ATTEMPT", "1") or "1")
    features = dict(FEATURE_DEFAULTS)
    features.update({
        "changed_files": len(changed_paths),
        "lines_added": added,
        "lines_deleted": deleted,
        "test_failure_count": int(junit["failures"] + junit["errors"]),
        "test_pass_rate": float(junit["pass_rate_percent"]),
        "code_quality_issues": quality_count,
        "security_findings": vuln_count,
        "pipeline_retries": max(0, attempt - 1),
        "config_change": int(config_change),
        "dependency_change": int(dependency_change),
        # No deployment-history telemetry exists in this first integration. Keep zero as a model input,
        # but explicitly mark it unmeasured so the score is never misrepresented as a research result.
        "recent_deploy_failures": 0,
    })
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(f"Demo model not found at {MODEL_PATH}; run scripts/train_demo_model.py first")
    bundle = joblib.load(MODEL_PATH)
    model = bundle["model"]
    feature_names = bundle.get("features", list(features))
    row = np.array([[features.get(name, 0) for name in feature_names]], dtype=float)
    score = float(model.predict_proba(row)[0][1])
    category = "HIGH" if score >= 0.67 else "MEDIUM" if score >= 0.34 else "LOW"
    advisory, explanation = classify_advisory(category, test_outcome, docker_outcome)

    run_id = os.getenv("GITHUB_RUN_ID")
    repo = os.getenv("GITHUB_REPOSITORY", "local")
    server = os.getenv("GITHUB_SERVER_URL", "https://github.com")
    run_url = f"{server}/{repo}/actions/runs/{run_id}" if run_id and repo != "local" else None
    metadata = {}
    try:
        metadata = json.loads(META_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass
    data_type = metadata.get("data_type", "UNKNOWN")
    measured = {
        "change_diff": diff_measured,
        "test_junit": junit["report_available"],
        "ruff_findings": quality_measured,
        "dependency_audit": security_measured,
        "deployment_history": False,
    }
    warnings = [
        "SYNTHETIC MODEL: the score is a pipeline-integration demonstration, not a validated deployment-failure probability or dissertation result.",
        "No deployment-history telemetry is connected; recent_deploy_failures is an unmeasured placeholder input.",
        "The model score never overrides test or container-build gates. No production deployment is performed by this workflow.",
    ]
    if not all(measured.values()):
        warnings.append("At least one feature source is unavailable or unmeasured; inspect the measured-source flags before interpreting this run.")

    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "run": {
            "repository": repo,
            "workflow": os.getenv("GITHUB_WORKFLOW", "local CI demonstration"),
            "run_id": run_id,
            "run_attempt": attempt,
            "event": event_name,
            "ref": os.getenv("GITHUB_REF", "local"),
            "commit_sha": os.getenv("GITHUB_SHA") or run_git(["rev-parse", "HEAD"]),
            "run_url": run_url,
        },
        "pipeline": {
            "tests": {**junit, "workflow_outcome": test_outcome},
            "static_analysis": {"tool": "Ruff", "outcome": ruff_outcome, "finding_count": quality_count, "report_available": quality_measured},
            "dependency_security": {"tool": "pip-audit", "outcome": security_outcome, "vulnerability_count": vuln_count, "report_available": security_measured},
            "container_build": {"outcome": docker_outcome},
        },
        "change_signals": {
            "changed_files": len(changed_paths),
            "lines_added": added,
            "lines_deleted": deleted,
            "changed_paths_sample": changed_paths[:50],
            "diff_measured": diff_measured,
            "config_change": config_change,
            "dependency_change": dependency_change,
        },
        "features_sent_to_demo_model": features,
        "feature_sources_measured": measured,
        "model_output": {
            "type": metadata.get("model_type", type(model).__name__),
            "training_data": data_type,
            "demo_score_percent": round(score * 100, 1),
            "demo_category": category,
            "validated_for_research": False,
        },
        "decision": {
            "advisory_status": advisory,
            "explanation": explanation,
            "production_deployment": "NOT_PERFORMED",
            "risk_score_controls_mandatory_gates": False,
        },
        "warnings": warnings,
    }


def render_markdown(report: dict[str, Any]) -> str:
    run = report["run"]
    model = report["model_output"]
    pipe = report["pipeline"]
    changes = report["change_signals"]
    decision = report["decision"]
    run_label = f"[open workflow]({run['run_url']})" if run.get("run_url") else "local execution"
    rows = [
        "# CI Deployment Risk Evidence — Synthetic Model Demo",
        "",
        f"- **Repository:** `{run['repository']}`",
        f"- **Event:** `{run['event']}`",
        f"- **Commit:** `{run['commit_sha']}`",
        f"- **Run:** {run_label}",
        "",
        "> **Research-integrity warning:** The model was trained on synthetic data. This score is plumbing/demo evidence only, not a validated probability, production decision, or dissertation result.",
        "",
        "## Pipeline evidence",
        "",
        "| Stage / signal | Observed value | Source status |",
        "|---|---:|---|",
        f"| Changed files | {changes['changed_files']} | {'measured' if changes['diff_measured'] else 'not measured'} |",
        f"| Lines added / deleted | {changes['lines_added']} / {changes['lines_deleted']} | {'measured' if changes['diff_measured'] else 'not measured'} |",
        f"| Tests | {pipe['tests']['failures'] + pipe['tests']['errors']} failed / {pipe['tests']['tests']} total | {'JUnit report' if pipe['tests']['report_available'] else 'fallback from step outcome'} |",
        f"| Test pass rate | {pipe['tests']['pass_rate_percent']}% | {'JUnit report' if pipe['tests']['report_available'] else 'fallback from step outcome'} |",
        f"| Ruff findings | {pipe['static_analysis']['finding_count']} | {'measured' if pipe['static_analysis']['report_available'] else 'not measured'}; step {pipe['static_analysis']['outcome']} |",
        f"| Dependency vulnerabilities | {pipe['dependency_security']['vulnerability_count']} | {'measured' if pipe['dependency_security']['report_available'] else 'not measured'}; step {pipe['dependency_security']['outcome']} |",
        f"| Docker build | {pipe['container_build']['outcome']} | build step |",
        f"| Config / dependency change | {changes['config_change']} / {changes['dependency_change']} | changed-path analysis |",
        "",
        "## Model demonstration",
        "",
        f"- **Synthetic demo score:** {model['demo_score_percent']}% (do not treat as a real-world failure probability)",
        f"- **Synthetic category:** {model['demo_category']}",
        f"- **Training data:** `{model['training_data']}`",
        f"- **Advisory status:** `{decision['advisory_status']}`",
        f"- **Explanation:** {decision['explanation']}",
        "",
        "## Unmeasured inputs and limitations",
        "",
    ]
    rows.extend([f"- {warning}" for warning in report["warnings"]])
    rows.extend(["", "## Measured-source flags", ""])
    rows.extend([f"- `{key}`: {'measured' if value else 'unmeasured/unavailable'}" for key, value in report["feature_sources_measured"].items()])
    rows.extend(["", "This workflow builds, tests, scans, and reports evidence. It does **not** deploy to production; the synthetic model score never overrides mandatory CI controls.", ""])
    return "\n".join(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--junitxml", type=Path, default=ROOT / "artifacts" / "pytest.xml")
    parser.add_argument("--ruff-report", type=Path, default=ROOT / "artifacts" / "ruff-report.json")
    parser.add_argument("--audit-report", type=Path, default=ROOT / "artifacts" / "pip-audit.json")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "artifacts")
    parser.add_argument("--tests-outcome", default="")
    parser.add_argument("--ruff-outcome", default="")
    parser.add_argument("--security-outcome", default="")
    parser.add_argument("--docker-outcome", default="")
    args = parser.parse_args()
    # Convert relative input paths to project-root-relative paths.
    for name in ("junitxml", "ruff_report", "audit_report", "out_dir"):
        value = getattr(args, name)
        if not value.is_absolute():
            setattr(args, name, ROOT / value)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    report = build_report(args)
    json_path = args.out_dir / "ci-risk-report.json"
    md_path = args.out_dir / "ci-risk-report.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    markdown = render_markdown(report)
    md_path.write_text(markdown, encoding="utf-8")
    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as handle:
            handle.write(markdown + "\n")
    print(markdown)
    print(f"\nWrote {json_path} and {md_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # workflow should expose why the evidence report failed
        print(f"CI risk report generation failed: {exc}", file=sys.stderr)
        raise

import json
from pathlib import Path

from scripts.ci_risk_assessment import classify_advisory, parse_audit, parse_junit, parse_ruff


def test_parse_junit_counts_failures_and_rate(tmp_path: Path):
    report = tmp_path / "junit.xml"
    report.write_text(
        '<testsuites><testsuite tests="4" failures="1" errors="0" skipped="1">'
        '<testcase/><testcase/><testcase><failure/></testcase><testcase><skipped/></testcase>'
        '</testsuite></testsuites>', encoding="utf-8"
    )
    parsed = parse_junit(report, "failure")
    assert parsed["report_available"] is True
    assert parsed["tests"] == 4
    assert parsed["failures"] == 1
    assert parsed["skipped"] == 1
    assert parsed["pass_rate_percent"] == 66.67


def test_parse_ruff_and_audit_reports(tmp_path: Path):
    ruff = tmp_path / "ruff.json"
    ruff.write_text(json.dumps([{"code": "E501"}, {"code": "F401"}]), encoding="utf-8")
    assert parse_ruff(ruff) == (2, True)

    audit = tmp_path / "audit.json"
    audit.write_text(json.dumps({"dependencies": [
        {"name": "a", "version": "1", "vulns": [{"id": "CVE-1"}, {"id": "CVE-2"}]},
        {"name": "b", "version": "1", "vulns": []},
    ]}), encoding="utf-8")
    assert parse_audit(audit) == (2, True)


def test_mandatory_ci_gates_override_advisory_model():
    status, _ = classify_advisory("LOW", "failure", "success")
    assert status == "BLOCKED_BY_EXISTING_CI_GATE"
    status, _ = classify_advisory("HIGH", "success", "success")
    assert status == "REVIEW_ADVISED_DEMO_ONLY"

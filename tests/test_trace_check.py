"""Tests for trace_check.py. Run with:  python -m pytest"""

import csv
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import trace_check  # noqa: E402

SAMPLE = os.path.join(os.path.dirname(__file__), "..", "sample_data")


def make_req(req_id, priority="High"):
    return {"req_id": req_id, "description": f"Requirement {req_id}", "priority": priority}


def make_test(test_id, req_ids, status="pass"):
    return {"test_id": test_id, "title": f"Test {test_id}", "req_ids": req_ids, "status": status}


def test_fully_covered_and_passing():
    result = trace_check.build_trace([make_req("R1"), make_req("R2")], [make_test("T1", "R1"), make_test("T2", "R2")])
    assert result["coverage"] == 100.0
    assert result["uncovered"] == []
    assert not trace_check.has_problems(result)


def test_uncovered_requirement_is_reported():
    result = trace_check.build_trace([make_req("R1"), make_req("R2")], [make_test("T1", "R1")])
    assert result["uncovered"] == ["R2"]
    assert result["coverage"] == 50.0
    assert trace_check.has_problems(result)


def test_one_test_can_cover_several_requirements():
    result = trace_check.build_trace([make_req("R1"), make_req("R2")], [make_test("T1", "R1; R2")])
    assert result["uncovered"] == []
    assert result["matrix"]["R2"] == [("T1", "pass")]


def test_broken_link_to_unknown_requirement():
    result = trace_check.build_trace([make_req("R1")], [make_test("T1", "R1;R9")])
    assert result["broken_links"] == [("T1", "R9")]


def test_failing_and_unrun_tests_are_flagged_but_still_count_as_coverage():
    result = trace_check.build_trace(
        [make_req("R1"), make_req("R2")], [make_test("T1", "R1", "fail"), make_test("T2", "R2", "Not Run")]
    )
    assert result["uncovered"] == []
    assert result["not_passing"] == ["R1", "R2"]


def test_invalid_status_is_reported():
    result = trace_check.build_trace([make_req("R1")], [make_test("T1", "R1", "passed")])
    assert result["bad_statuses"] == [("T1", "passed")]


def test_duplicate_ids_are_reported():
    result = trace_check.build_trace([make_req("R1"), make_req("R1")], [make_test("T1", "R1"), make_test("T1", "R1")])
    assert result["duplicate_reqs"] == ["R1"]
    assert result["duplicate_tests"] == ["T1"]


def test_empty_requirements_do_not_crash():
    result = trace_check.build_trace([], [])
    assert result["coverage"] == 0.0


def test_missing_column_raises_clear_error(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("req_id,description\nR1,Something\n")
    with pytest.raises(ValueError, match="priority"):
        trace_check.load_csv(bad, trace_check.REQUIREMENT_COLUMNS)


def test_sample_data_end_to_end(tmp_path, capsys):
    matrix = tmp_path / "matrix.csv"
    exit_code = trace_check.main([
        os.path.join(SAMPLE, "requirements.csv"),
        os.path.join(SAMPLE, "test_cases.csv"),
        "--matrix", str(matrix),
    ])
    output = capsys.readouterr().out

    assert exit_code == 1  # the sample data has gaps on purpose
    assert "Coverage:     90.0%" in output
    assert "REQ-009" in output  # no test case
    assert "TC-009 -> REQ-011" in output  # broken link

    rows = {row["req_id"]: row for row in csv.DictReader(matrix.open())}
    assert rows["REQ-001"]["trace_status"] == "VERIFIED"
    assert rows["REQ-004"]["trace_status"] == "IN PROGRESS"
    assert rows["REQ-009"]["trace_status"] == "NOT COVERED"

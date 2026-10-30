"""Requirements traceability checker.

Reads a requirements CSV and a test cases CSV, links them, and reports:
  - requirements with no test case (coverage gaps)
  - test cases that point to requirement IDs that don't exist (broken links)
  - requirements whose linked tests failed or haven't run yet
  - overall coverage percentage

Optionally writes a traceability matrix (one row per requirement) to CSV.

Usage:
    python trace_check.py sample_data/requirements.csv sample_data/test_cases.csv
    python trace_check.py reqs.csv tests.csv --matrix matrix.csv
"""

import argparse
import csv
import sys

REQUIREMENT_COLUMNS = ["req_id", "description", "priority"]
TEST_COLUMNS = ["test_id", "title", "req_ids", "status"]
VALID_STATUSES = {"pass", "fail", "not run"}


def load_csv(path, required_columns):
    """Read a CSV file into a list of dicts, checking that the needed columns exist."""
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = [col for col in required_columns if col not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{path} is missing column(s): {', '.join(missing)}")
        # Strip stray spaces from every value so " REQ-001" matches "REQ-001".
        return [{key: (value or "").strip() for key, value in row.items()} for row in reader]


def find_duplicates(ids):
    """Return IDs that appear more than once, in the order first seen."""
    seen, duplicates = set(), []
    for item in ids:
        if item in seen and item not in duplicates:
            duplicates.append(item)
        seen.add(item)
    return duplicates


def build_trace(requirements, tests):
    """Link each requirement to the test cases that cover it.

    Returns a dict with the matrix and every problem found.
    """
    req_ids = [r["req_id"] for r in requirements]
    known = set(req_ids)

    # matrix: req_id -> list of (test_id, status) tuples
    matrix = {req_id: [] for req_id in req_ids}
    broken_links = []  # (test_id, unknown req_id)
    bad_statuses = []  # (test_id, status as written)

    for test in tests:
        status = test["status"].lower()
        if status not in VALID_STATUSES:
            bad_statuses.append((test["test_id"], test["status"]))

        # A test can cover several requirements, separated by semicolons.
        for req_id in [r.strip() for r in test["req_ids"].split(";") if r.strip()]:
            if req_id in known:
                matrix[req_id].append((test["test_id"], status))
            else:
                broken_links.append((test["test_id"], req_id))

    uncovered = [req_id for req_id, linked in matrix.items() if not linked]
    not_passing = [
        req_id for req_id, linked in matrix.items()
        if linked and any(status != "pass" for _, status in linked)
    ]
    total_unique = len(matrix)
    covered = total_unique - len(uncovered)
    coverage = (covered / total_unique * 100) if total_unique else 0.0

    return {
        "matrix": matrix,
        "uncovered": uncovered,
        "broken_links": broken_links,
        "not_passing": not_passing,
        "bad_statuses": bad_statuses,
        "duplicate_reqs": find_duplicates(req_ids),
        "duplicate_tests": find_duplicates([t["test_id"] for t in tests]),
        "coverage": coverage,
    }


def print_report(result, requirements):
    """Print a readable summary to the screen."""
    priority = {r["req_id"]: r["priority"] for r in requirements}
    total = len(result["matrix"])

    print("REQUIREMENTS TRACEABILITY REPORT")
    print("=" * 40)
    print(f"Requirements: {total}")
    print(f"Coverage:     {result['coverage']:.1f}% ({total - len(result['uncovered'])} of {total} have at least one test)")
    print()

    sections = [
        ("Requirements with no test case", [f"{r} (priority: {priority.get(r) or 'none'})" for r in result["uncovered"]]),
        ("Test cases linked to unknown requirements", [f"{t} -> {r}" for t, r in result["broken_links"]]),
        ("Requirements with failing or unrun tests", result["not_passing"]),
        ("Test cases with an invalid status", [f"{t}: '{s}'" for t, s in result["bad_statuses"]]),
        ("Duplicate requirement IDs", result["duplicate_reqs"]),
        ("Duplicate test IDs", result["duplicate_tests"]),
    ]
    for title, items in sections:
        print(f"{title}: {len(items)}")
        for item in items:
            print(f"  - {item}")
    print()


def write_matrix(result, requirements, path):
    """Write one row per requirement showing its linked tests and their statuses."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["req_id", "description", "priority", "test_ids", "statuses", "trace_status"])
        for req in requirements:
            linked = result["matrix"].get(req["req_id"], [])
            if not linked:
                trace_status = "NOT COVERED"
            elif all(status == "pass" for _, status in linked):
                trace_status = "VERIFIED"
            else:
                trace_status = "IN PROGRESS"
            writer.writerow([
                req["req_id"], req["description"], req["priority"],
                "; ".join(t for t, _ in linked),
                "; ".join(s for _, s in linked),
                trace_status,
            ])


def has_problems(result):
    """True if anything should block sign-off (used for the exit code)."""
    return any(result[key] for key in
               ["uncovered", "broken_links", "bad_statuses", "duplicate_reqs", "duplicate_tests"])


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check that every requirement is covered by a test case.")
    parser.add_argument("requirements", help="CSV with columns: " + ", ".join(REQUIREMENT_COLUMNS))
    parser.add_argument("tests", help="CSV with columns: " + ", ".join(TEST_COLUMNS))
    parser.add_argument("--matrix", help="optional path to write a traceability matrix CSV")
    args = parser.parse_args(argv)

    try:
        requirements = load_csv(args.requirements, REQUIREMENT_COLUMNS)
        tests = load_csv(args.tests, TEST_COLUMNS)
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    result = build_trace(requirements, tests)
    print_report(result, requirements)

    if args.matrix:
        write_matrix(result, requirements, args.matrix)
        print(f"Traceability matrix written to {args.matrix}")

    # Exit code 1 lets a build pipeline fail when traceability has gaps.
    return 1 if has_problems(result) else 0


if __name__ == "__main__":
    sys.exit(main())

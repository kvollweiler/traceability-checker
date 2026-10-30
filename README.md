# Requirements Traceability Checker

A small Python command-line tool that checks whether every requirement in a project is covered by at least one test case, and flags the gaps a reviewer would otherwise find by hand.

I built this because tracing requirements to test cases was part of my day-to-day work as a technical writer on transaction-processing systems, and checking a traceability matrix manually is slow and easy to get wrong.

## What it checks

| Check | Why it matters |
|---|---|
| Requirements with no test case | A requirement nobody tests can ship broken. |
| Test cases that point to unknown requirement IDs | Usually a typo or a deleted requirement; the link is broken either way. |
| Requirements whose tests failed or haven't run | Covered on paper, but not yet verified. |
| Invalid test statuses | Keeps the data clean (`pass`, `fail`, `not run`). |
| Duplicate requirement or test IDs | Duplicates make every count unreliable. |

It also reports overall coverage and can export a traceability matrix CSV with one row per requirement, marked `VERIFIED`, `IN PROGRESS`, or `NOT COVERED`.

## Requirements

Python 3.9 or later. The tool itself uses only the standard library; the tests use `pytest`.

## Usage

```
python trace_check.py sample_data/requirements.csv sample_data/test_cases.csv
python trace_check.py sample_data/requirements.csv sample_data/test_cases.csv --matrix matrix.csv
```

### Input format

**requirements.csv**

| Column | Example |
|---|---|
| `req_id` | `REQ-004` |
| `description` | `System flags forms that are within 3 days of their due date` |
| `priority` | `High` |

**test_cases.csv**

| Column | Example |
|---|---|
| `test_id` | `TC-006` |
| `title` | `Supervisor overdue dashboard lists all overdue forms` |
| `req_ids` | `REQ-005;REQ-006` (separate several IDs with semicolons) |
| `status` | `pass`, `fail`, or `not run` |

### Sample output

The sample data describes a fictional form-tracking system and contains deliberate gaps:

```
REQUIREMENTS TRACEABILITY REPORT
========================================
Requirements: 10
Coverage:     90.0% (9 of 10 have at least one test)

Requirements with no test case: 1
  - REQ-009 (priority: Medium)
Test cases linked to unknown requirements: 1
  - TC-009 -> REQ-011
Requirements with failing or unrun tests: 3
  - REQ-004
  - REQ-005
  - REQ-006
Test cases with an invalid status: 0
Duplicate requirement IDs: 0
Duplicate test IDs: 0
```

### Exit codes

| Code | Meaning |
|---|---|
| `0` | No traceability problems found |
| `1` | Problems found (uncovered requirements, broken links, invalid statuses, or duplicates) |
| `2` | A file couldn't be read or is missing a required column |

Because problems return exit code `1`, the checker can run in a build pipeline and stop a release when traceability has gaps. Failing or unrun tests are reported but don't change the exit code, since they're normal while testing is still in progress.

## Running the tests

```
pip install pytest
python -m pytest -v
```

The tests run automatically on every push through GitHub Actions (`.github/workflows/tests.yml`).

## Ideas for next versions

- Read requirements and test cases directly from Excel files
- Filter the report by priority (for example, show only uncovered High requirements)
- Produce an HTML report
- Pull test cases from a Jira export

## About this project

Developed with Claude as a pair-programming assistant. All sample data is fictional.

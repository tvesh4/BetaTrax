# BetaTrax Sprint 3 — Sub-project 1: Developer Effectiveness Metric + Coverage

**Date:** 2026-04-27
**Author:** Claude (brainstormed with dalight-luckyw)
**Status:** Approved for planning
**Scope:** Sub-project 1 of 4 in Sprint 3. Delivers the developer-effectiveness classifier (Sprint 3 §19–25) with full statement and branch coverage via `coverage.py`, plus the prerequisite work needed for any test to run at all.

This spec supersedes the deleted `2026-04-23-sprint3-unblock-and-tests-design.md` for the classifier portion. The endpoint smoke-test portion of that earlier spec moves to Sub-project 2 (separate spec).

## 1. Background

BetaTrax is at Sprint 3 with the deadline today (2026-04-27 23:59). The team has already begun migrating to PostgreSQL + `django-tenants` and has scaffolded the `get_developer_metric` endpoint inline in `BTAPI/views.py` (lines 70–87 as of this writing). However:

- `BTAPI/views.py` carries one unresolved Git merge-conflict block at lines 97–103. The file does not import; the server will not start; no tests can run.
- `BTAPI/tests.py` contains a single test that references the removed `ProductOwner` model and the removed `testerEmail` field. It cannot run even after the conflict is resolved.
- The active `DATABASES` configuration points at PostgreSQL with the `django_tenants` backend. Postgres is not running locally and no tenant schemas have been migrated, so the test runner has nowhere to bootstrap a test database.
- `coverage.py` is not in `requirements.txt`; there is no `.coveragerc`.

Sprint 3 §25 requires that "tests have satisfied the adequacy criteria of full statement coverage and full branch coverage" of the classifier. Achieving that with the current state is impossible, so this spec bundles three small unblock tasks with the classifier work to make the deliverable demonstrable.

## 2. Goals

1. Make `BTAPI/views.py` importable again with a correct, hybrid resolution of the lone merge conflict.
2. Make the test runner usable today, without requiring local PostgreSQL, via a test-only settings module.
3. Extract the classifier logic into a pure function in a new `BTAPI/metrics.py` module so `coverage.py` can measure it cleanly.
4. Add a focused test class with six cases that achieve full statement and full branch coverage of the classifier.
5. Wire `coverage.py` (with `branch = True`) and document the run commands in the README so the grader can reproduce the result.

## 3. Non-goals

- Endpoint-level smoke tests for any view (including `/api/metric/<id>/` itself) — these belong to Sub-project 2.
- Tightening the `IsAuthenticated`-only permission on `get_developer_metric` to `IsOwner | IsDeveloper`. Sprint 3 does not specify, and changing it adds risk.
- Fixing the pre-existing `id.title()` username-lookup bug on `get_developer_metric` (and other endpoints). Belongs to Sub-project 2 cleanup at the earliest.
- Verifying that `fixedCount` / `reopenedCount` counters are correctly maintained by `patch_update_report` end-to-end. That is an integration concern for Sub-project 2.
- Multi-tenancy completion (Sub-project 3), API documentation (Sub-project 4), or any Release 2 written documents.

## 4. Conflict resolution in `BTAPI/views.py`

The conflict block at lines 97–103:

```python
<<<<<<< Updated upstream
    # dev_id = request.query_params.get('dev')
    report = get_object_or_404(DefectReport, id=id.title())
=======
    dev_id = request.query_params.get('dev')
    report = get_object_or_404(DefectReport, id=id)
>>>>>>> Stashed changes
```

Neither side is correct standalone:

- The Upstream side comments out `dev_id`, but `dev_id` is referenced later at line 164 (`if dev_id: report.assignedToId_id = dev_id`). Choosing Upstream alone produces a `NameError` whenever the endpoint is hit.
- The Stashed side drops `id.title()`, but every other endpoint in `views.py` applies `.title()` for primary-key lookup. DefectReport PKs follow a TitleCase convention (e.g. `Def001`); choosing Stashed alone would silently 404 on any caller passing a lowercase ID.

**Resolution:** hybrid — take the `dev_id` line from Stashed, keep `id.title()` from Upstream:

```python
    dev_id = request.query_params.get('dev')
    report = get_object_or_404(DefectReport, id=id.title())
```

The `.title()` convention itself is fragile and silently breaks if the PK convention changes. Out of scope for this spec; tagged for Sub-project 2 cleanup.

## 5. Test-only settings module

### 5.1 New file `BTConfig/settings_test.py`

```python
from .settings import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}
DATABASE_ROUTERS = ()
INSTALLED_APPS = [a for a in INSTALLED_APPS if a != 'django_tenants']
MIDDLEWARE = [m for m in MIDDLEWARE if 'django_tenants' not in m]
```

### 5.2 Usage

```bash
python3 manage.py test --settings=BTConfig.settings_test BTAPI
```

### 5.3 Caveats (must appear in the README)

- Tests do **not** exercise tenant isolation behaviour. A second pass under the real Postgres + tenants configuration is required once Sub-project 3 lands.
- `BTAPI/models.py` still imports `TenantMixin` / `DomainMixin` for `Client` / `Domain`, so the venv must have `django-tenants` installed (it is already in `requirements.txt`). Stripping it from `INSTALLED_APPS` is sufficient — Django will still create the `Client` / `Domain` tables in SQLite, which is harmless because the test suite does not touch them.
- `TENANT_MODEL` and `TENANT_DOMAIN_MODEL` settings remain inherited from the base settings module. Without the routers and middleware they are inert.
- The classifier coverage requirement (Sprint 3 §25) is satisfied by pure-function unit tests that never touch the database, so this option-A trade-off does not affect grading on the classifier.

## 6. Classifier extraction

### 6.1 New module `BTAPI/metrics.py`

```python
def classify_developer_effectiveness(fixed_count: int, reopened_count: int) -> str:
    if fixed_count < 20:
        return "Insufficient data"
    ratio = reopened_count / fixed_count
    if ratio < 1/32:
        return "Good"
    if ratio < 1/8:
        return "Fair"
    return "Poor"
```

### 6.2 Updated view in `BTAPI/views.py`

```python
from .metrics import classify_developer_effectiveness

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_developer_metric(request, id):
    developer = get_object_or_404(Developer, user__username=id.title())
    report = classify_developer_effectiveness(
        developer.fixedCount, developer.reopenedCount
    )
    return Response({"report": report})
```

### 6.3 Rationale

- The current view uses Python `match`/`case` with guard expressions. `coverage.py` can measure these but its branch tracking on guard patterns is uneven. Plain `if/elif/else` produces unambiguous branch counts and a stable percentage.
- Extracting to `BTAPI/metrics.py` lets the test suite call the classifier directly without the HTTP / DB layer, so coverage of the algorithm is decoupled from coverage of the view.
- The thresholds use the literal expressions `1/32` and `1/8`. Both evaluate to exact IEEE 754 floats (`0.03125`, `0.125`) because they are reciprocals of powers of two, so boundary tests are deterministic.
- The `id.title()` lookup, the `IsAuthenticated`-only permission, and the inline `match`/`case` increment counters elsewhere in `views.py` are preserved unchanged. This is a behaviour-preserving extraction.

## 7. Test suite

### 7.1 Location and class

A single new class `ClassifierTests(SimpleTestCase)` in `BTAPI/tests.py`. `SimpleTestCase` (not `TestCase`) because the classifier never touches the database — this also keeps the suite fast and unaffected by any tenancy concern.

### 7.2 Cases

Six cases covering every statement and both directions of every branch:

| # | Case | fixed | reopened | ratio | Expected | Branch covered |
|---|---|---|---|---|---|---|
| 1 | below threshold, zero data | 0 | 0 | — | `Insufficient data` | `fixed_count < 20` true |
| 2 | just below threshold | 19 | 0 | — | `Insufficient data` | `fixed_count < 20` true |
| 3 | at threshold, ratio = 0 | 20 | 0 | 0.0 | `Good` | `fixed_count < 20` false, `ratio < 1/32` true |
| 4 | ratio = 1/32 exactly | 32 | 1 | 0.03125 | `Fair` | `ratio < 1/32` false (boundary), `ratio < 1/8` true |
| 5 | ratio between 1/32 and 1/8 | 32 | 3 | 0.09375 | `Fair` | `ratio < 1/32` false, `ratio < 1/8` true |
| 6 | ratio = 1/8 exactly | 32 | 4 | 0.125 | `Poor` | `ratio < 1/8` false (boundary), fallthrough |

Cases 1 and 3 force the `fixed_count < 20` branch in both directions. Cases 4 and 6 pin the strict-`<` boundary semantics — these are the cases most likely to catch a future `<=` regression. Case 5 exercises `Fair` on a non-boundary ratio.

### 7.3 Cleanup of existing broken test

Delete `DefectReportTestCase` in `BTAPI/tests.py`. It references the removed `ProductOwner` model and the removed `testerEmail` field, so it cannot run. Sub-project 2 will replace it with proper `APITestCase` coverage that drives model creation through real endpoints.

## 8. Coverage configuration

### 8.1 Add to `requirements.txt`

```
coverage==7.6.10
```

### 8.2 New `.coveragerc` at the project root

```ini
[run]
branch = True
source = BTAPI
omit =
    BTAPI/migrations/*
    BTAPI/tests.py
    BTAPI/__init__.py
    BTAPI/admin.py
    BTAPI/apps.py

[report]
show_missing = True
skip_covered = False
precision = 1
```

`branch = True` is what enables branch-coverage measurement — Sprint 3 §25 requires it. `source = BTAPI` scopes measurement to app code; Django and DRF internals are excluded automatically. Migrations, tests, and trivial config files are omitted so the headline percentage reflects production code.

### 8.3 Run commands (also documented in README)

```bash
coverage run --rcfile=.coveragerc manage.py test --settings=BTConfig.settings_test BTAPI
coverage report -m
coverage report -m --include='BTAPI/metrics.py'   # classifier-only view for the rubric
coverage html                                       # optional: htmlcov/index.html
```

The third command isolates `BTAPI/metrics.py` so the team can show the grader a clean 100% statement and 100% branch line for the classifier specifically — the Sprint 3 grading hook.

## 9. README updates

Add a new "Testing & Coverage" section with:

1. A note that the active settings target Postgres + django-tenants, but a SQLite test-only settings module is provided for fast local runs.
2. The four `coverage` commands above.
3. The expected output: a single line in the third command's report showing `BTAPI/metrics.py` at 100% statement and 100% branch coverage.

## 10. Acceptance criteria

1. `python3 -c "import BTAPI.views"` returns no error.
2. `python3 manage.py test --settings=BTConfig.settings_test BTAPI` runs and reports six tests passing in `ClassifierTests`.
3. `coverage report -m --include='BTAPI/metrics.py'` shows 100% statement coverage and 100% branch coverage for `BTAPI/metrics.py`.
4. The endpoint `GET /api/metric/<username>/` continues to return `{"report": "<classification>"}` identical to today's behaviour for any given `(fixedCount, reopenedCount)` pair.
5. README documents the test and coverage commands.

## 11. Out-of-scope items tagged for follow-up

- Endpoint smoke tests (Sub-project 2 spec).
- Permission tightening on `/api/metric/<id>/` (Sub-project 2 cleanup).
- The `id.title()` username-lookup bug (Sub-project 2 cleanup).
- Counter-increment integration tests in `patch_update_report` (Sub-project 2).
- Multi-tenancy completion (Sub-project 3).
- API documentation generation (Sub-project 4).

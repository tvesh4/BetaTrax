# BetaTrax Sprint 3 — Unblock + Tests & Coverage (Sub-projects A + D)

**Date:** 2026-04-23
**Author:** Claude (brainstormed with dalight-luckyw)
**Scope:** Sub-project A (resolve outstanding merge conflicts in `BTAPI/views.py` and fix the developer-metric counter logic) and sub-project D (automated tests + coverage) from the Sprint 3 breakdown. Sub-projects B (multi-tenancy completion), E (API documentation), and F (Release 2 documents) are out of scope for this spec.

## 1. Background & Motivation

BetaTrax is at Sprint 3. The team has already begun migrating to PostgreSQL and wiring in `django-tenants`, and has scaffolded the developer-effectiveness metric endpoint. However, `BTAPI/views.py` is currently in a broken state — it carries unresolved Git merge-conflict markers at four locations (lines 19, 122, 147, 208 as of commit `ec738a3`). The file cannot be imported, so the server cannot start and no tests can run. Sprint 3 also introduces a hard requirement for automated tests: one representative test per endpoint method, and statement-plus-branch coverage of the developer-effectiveness classifier via `coverage.py`.

The local development environment is not yet ready to run these tests against Postgres + django-tenants: `psycopg2` and `django_tenants` are missing from the active venv, Postgres is not installed on this machine, and Docker is not running. This spec therefore introduces a test-only Django settings module that runs the test suite against in-memory SQLite with the tenants layer stripped, so the team can make progress on test code today. A second pass (outside this spec) will bring up Postgres + tenants and re-run the suite under the "real" configuration.

## 2. Goals

1. Make `BTAPI/views.py` importable again with correct `fixedCount` / `reopenedCount` increment logic.
2. Extract the classifier into a pure function so `coverage.py` can measure it cleanly.
3. Provide a test-only settings module so tests run locally on SQLite today.
4. Add a test suite that gives (a) one happy-path test per endpoint method and (b) full statement-and-branch coverage on the classifier.
5. Wire `coverage.py` with a `.coveragerc` and document the commands.

## 3. Non-goals

- Installing or configuring PostgreSQL on the developer machine.
- Finalising the multi-tenancy feature (URL routing, admin registration for `Client`/`Domain`, tenant bootstrap).
- Generating API documentation (e.g., drf-spectacular).
- Writing Release 2 use cases, refined product backlog, or sprint backlog documents.
- Full test coverage of every view. Only the classifier requires full coverage; other views get a representative smoke test each.

## 4. Conflict Resolution Policy for `BTAPI/views.py`

All four conflicts will resolve to the **Upstream** side, because the **Stashed** side references models and fields that no longer exist (the `ProductOwner` model was removed in migration `0044`, and `testerEmail` was removed in migration `0034`). Two small corrections are layered on top of the Upstream choice:

### 4.1 Conflict at `post_new_report` (lines 19–23)

Upstream and Stashed are semantically equivalent (`obj.attr` vs `getattr(obj, 'attr', None)`), but Upstream is cleaner. Keep Upstream:

```python
if report.productId.ownerId and report.productId.ownerId.email:
```

### 4.2 Conflict in `NEW → CLOSED` duplicate-link branch (lines 122–138)

Upstream has the right control flow but assigns a `DefectReport` instance to the `_id` attribute of an FK (`report.parent_id = new_parent_id`), which is wrong Django ORM usage. Fix:

```python
if new_parent:
    parent_report = get_object_or_404(DefectReport, id=new_parent)
    report.parent = parent_report
    if parent_report.testerId.email:
        send_duplicate_update_email(parent_report, report)
        send_duplicate_update_email(report, parent_report)
```

Additionally, preserve Stashed's else-branch that handles the case where a report already has a parent linked (the "resend" notification path), since Upstream dropped it:

```python
elif report.parent:
    if report.parent.testerId.email:
        send_duplicate_update_email(report.parent, report)
        send_duplicate_update_email(report, report.parent)
```

### 4.3 Conflict in `ASSIGNED → FIXED / CLOSED` branch (lines 147–160)

Keep Upstream — Sprint 3 requires the `fixedCount` increment. The `elif new_status == 'Closed'` branch stays (Sprint 2's "cannot reproduce" path does not bump any counter):

```python
case 'Assigned':
    if is_developer:
        if new_status == 'Fixed':
            report.status = new_status
            status_changed = True
            request.user.developer_profile.fixedCount += 1
            request.user.developer_profile.save()
        elif new_status == 'Closed':
            report.status = new_status
            status_changed = True
```

### 4.4 Conflict in `post_new_product` (lines 208–216)

Keep Upstream. Stashed calls `ProductOwner.objects.get(...)`, but `ProductOwner` was deleted in migration `0044`. `Product.ownerId` is now an FK to `AUTH_USER_MODEL`, so `serializer.save(ownerId=request.user)` is the correct assignment:

```python
serializer.save(ownerId=request.user)
```

### 4.5 Net effect after resolution

- `fixedCount` increments when the acting developer marks their own assigned report `Fixed`.
- `reopenedCount` increments on the currently-assigned developer when the PO moves `Fixed → Reopened` (via the existing Upstream logic around `report.assignedToId.developer_profile.reopenedCount += 1`).
- These match Sprint 3 §19–24.

## 5. Classifier Extraction

### 5.1 New module `BTAPI/metrics.py`

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

### 5.2 Updated view `get_developer_metric`

```python
from .metrics import classify_developer_effectiveness

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_developer_metric(request, id):
    developer = get_object_or_404(Developer, user__username=id)
    report = classify_developer_effectiveness(
        developer.fixedCount, developer.reopenedCount
    )
    return Response({"report": report})
```

### 5.3 Rationale

- Unit tests exercise pure arithmetic without the HTTP/DB layer.
- `coverage.py` reports clean numbers on a 6-line function.
- The classifier is reusable for any future dashboard or summary view.

## 6. Test-only Settings Module

### 6.1 New file `BTConfig/settings_test.py`

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

### 6.2 Usage

```bash
python3 manage.py test --settings=BTConfig.settings_test BTAPI
```

### 6.3 Known caveats

- `BTAPI/models.py` defines `Client(TenantMixin)` and `Domain(DomainMixin)`. These imports require `django_tenants` to be installed in the venv (it is listed in `requirements.txt`; a `pip install -r requirements.txt` is a prerequisite). Under SQLite with `django_tenants` stripped from `INSTALLED_APPS`, Django will still create the `Client`/`Domain` tables because their models belong to `BTAPI`; that is acceptable — the test suite does not touch them.
- `TENANT_MODEL` / `TENANT_DOMAIN_MODEL` remain in settings but are harmless without the routers/middleware.
- Tests do not exercise the tenant isolation behaviour. A second pass (once Postgres + tenants are up) must re-run the suite under the default settings.

## 7. Test Suite

### 7.1 File layout

Single file `BTAPI/tests.py` containing three test classes.

### 7.2 `ClassifierTests(TestCase)` — full coverage of the classifier

Six cases covering every statement and both directions of every branch:

| Case | fixed | reopened | ratio | Expected |
|---|---|---|---|---|
| below-threshold | 0 | 0 | — | `Insufficient data` |
| just-below-threshold | 19 | 0 | — | `Insufficient data` |
| at-threshold, ratio=0 | 20 | 0 | 0 | `Good` |
| ratio = 1/32 exactly | 32 | 1 | 0.03125 | `Fair` (strict `<` boundary) |
| ratio = 1/8 exactly | 32 | 4 | 0.125 | `Poor` (strict `<` boundary) |
| ratio between 1/32 and 1/8 | 32 | 3 | 0.09375 | `Fair` |

### 7.3 `EndpointSmokeTests(APITestCase)` — one happy-path test per endpoint method

`setUpTestData` creates:
- `User`, `Developer`, `Owner` groups (by name).
- One `AUTH_USER_MODEL` user per role (`tester`, `dev`, `po`), all with `email`.
- One `Developer` profile for `dev` with `fixedCount=0`, `reopenedCount=0`.
- One `Product` with `ownerId=po`, `devId=dev`.
- One `DefectReport` (`status=New`, `testerId=tester`, `productId=<product>`).

Ten tests, each asserting a 2xx status and any invariant obvious from the endpoint:
1. `POST /api/token/` — returns `access` + `refresh`.
2. `POST /api/token/refresh/` — returns a new `access` given a valid `refresh`.
3. `POST /api/defect/` — creates a report with `status=New`.
4. `GET /api/reports/OPEN/` — returns a list (may be empty).
5. `GET /api/reports/assigned/dev=<id>/` — returns either a list or the "no assigned reports" message.
6. `GET /api/defect/<id>/` — returns the full serialised report.
7. `PATCH /api/update/<id>/?status=Open` as `po` — moves the seed report `New → Open`.
8. `POST /api/comment/<id>/` — creates a comment linked to the seed report.
9. `POST /api/product/` as `po` — creates a new product.
10. `GET /api/metric/<dev-username>/` — returns `{"report": "Insufficient data"}` given counters of `(0, 0)`.

### 7.4 `MetricEndpointIntegrationTest(APITestCase)` — small end-to-end check

Using the `EndpointSmokeTests` fixtures, this test exercises the PATCH counter-increment path through the API. It creates 20 additional `DefectReport` rows assigned to `dev`, then for each one issues `PATCH /api/update/<id>/?status=Fixed` authenticated as `dev`. After the loop, `Developer.fixedCount` should read 20 and `GET /api/metric/<dev-username>/` should return `{"report": "Good"}` (ratio = 0, below the 1/32 threshold). This confirms Section 4 (the ASSIGNED → FIXED resolution) and Section 5 (the classifier) compose correctly through the real view.

### 7.5 Model change required to keep tests terse

`Developer.fixedCount` and `Developer.reopenedCount` currently have no `default`. Tests (and admin ergonomics) improve with `default=0`. This is a single migration, `0049_default_developer_counts.py`, generated by `makemigrations`.

## 8. Coverage Configuration

### 8.1 New file `.coveragerc`

```ini
[run]
source = BTAPI
omit =
    BTAPI/migrations/*
    BTAPI/tests.py
    BTAPI/admin.py
    BTAPI/apps.py
branch = True

[report]
show_missing = True
```

### 8.2 `requirements.txt` addition

```
coverage==7.*
```

### 8.3 Commands (to be documented in README)

```bash
coverage run --source=BTAPI manage.py test --settings=BTConfig.settings_test BTAPI
coverage report -m
coverage html   # optional — produces htmlcov/ for the demo
```

### 8.4 Coverage target

- `BTAPI/metrics.py`: **100% statement coverage, 100% branch coverage**.
- Other modules: incidental — the spec requires full coverage only on the classifier.

## 9. Commit Strategy

Separate commits on branch `dev`, no pushes, so each change can be reviewed or reverted independently:

1. `fix(views): resolve merge conflicts, correct duplicate-link ORM usage`
2. `refactor(metrics): extract classify_developer_effectiveness pure fn`
3. `feat(models): default 0 for Developer.fixedCount/reopenedCount + migration`
4. `chore(test-env): add BTConfig/settings_test for local SQLite runs`
5. `test: add classifier coverage suite + endpoint smoke tests`
6. `chore(deps): add coverage; add .coveragerc; docs(readme): testing instructions`

## 10. Risks & Open Questions

- **Second-pass validation under Postgres + tenants is outside this spec.** The SQLite test suite may pass while a tenant-scoped path fails, because `django_tenants` is stripped from the test config. Mitigation: schedule the re-run once sub-project B is done.
- **`Client` / `Domain` tables in SQLite.** If Django's migration runner errors on the tenants mixins under SQLite, a fallback is to conditionally define `Client`/`Domain` only when `django_tenants` is in `INSTALLED_APPS`. This is not expected to trigger but is noted.
- **Existing `Developer` rows** created before migration `0049` will already have integer values set (the field was non-null). The default only affects future inserts, so the migration is safe.
- **`PATCH /api/update/` is tested only for `New → Open`** (one representative case per spec §38). Other transitions are implicitly exercised by `MetricEndpointIntegrationTest`. If the team wants more coverage of the transition table, that is a follow-up.

## 11. Deliverables Checklist

- [ ] `BTAPI/views.py` is importable (no conflict markers) and behaves per Section 4.5.
- [ ] `BTAPI/metrics.py` exists with `classify_developer_effectiveness`.
- [ ] `get_developer_metric` delegates to the new function.
- [ ] `BTConfig/settings_test.py` exists and is used by the test commands.
- [ ] `Developer` has `default=0` on both counter fields, with a new migration.
- [ ] `BTAPI/tests.py` contains `ClassifierTests`, `EndpointSmokeTests`, `MetricEndpointIntegrationTest`.
- [ ] `.coveragerc` exists.
- [ ] `requirements.txt` lists `coverage`.
- [ ] README has a "Running tests" section with the commands from §8.3.
- [ ] `coverage report` shows 100% statement + branch on `BTAPI/metrics.py`.

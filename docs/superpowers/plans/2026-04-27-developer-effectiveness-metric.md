# Developer Effectiveness Metric Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver Sprint 3 sub-project 1 — extract the developer-effectiveness classifier into a pure function, achieve 100% statement and branch coverage on it via `coverage.py`, and unblock the test runner so the work is demonstrable today.

**Architecture:** Three small unblock changes (resolve a Git merge conflict, delete a broken stale test, add a SQLite test-only Django settings module) precede the actual feature work (extract classifier into `BTAPI/metrics.py`, add a six-case `SimpleTestCase`, wire `coverage.py` with `branch = True`, document run commands in README). The classifier extraction is behaviour-preserving — the view's URL, permission, and lookup logic stay identical.

**Tech Stack:** Python 3.10+, Django 6.0.3, Django REST Framework 3.17.1, `coverage.py` 7.6.10, SQLite (test runtime only).

**Design spec:** `docs/superpowers/specs/2026-04-27-developer-effectiveness-metric-design.md`

---

## Pre-flight

Verify you are at the project root and on the right branch.

- [ ] **Pre-flight Step 1: Confirm working directory and branch**

```bash
pwd
git branch --show-current
git status --short
```

Expected: `pwd` ends in `BetaTrax`. Branch is `dev`. Status shows `UU BTAPI/views.py` among other entries — that unmerged conflict is what Task 1 fixes.

- [ ] **Pre-flight Step 2: Confirm Python virtualenv is active**

```bash
which python3
python3 -c "import django; print(django.get_version())"
```

Expected: `which python3` points inside `venv/`. Django version prints `6.0.3`. If not, run `source venv/bin/activate` and retry.

- [ ] **Pre-flight Step 3: Confirm `django-tenants` is installed (needed for models.py to import even when tests strip tenants)**

```bash
python3 -c "import django_tenants; print(django_tenants.__version__)"
```

Expected: a version string prints (e.g. `3.10.1`). If `ModuleNotFoundError`, run `pip install -r requirements.txt` and retry.

---

## Task 1: Resolve the merge conflict in `BTAPI/views.py`

The lone unresolved conflict block at `BTAPI/views.py:97–103` blocks `import BTAPI.views`, which means the server won't start and no tests can run. This task applies the hybrid resolution from the spec (§4): take `dev_id = ...` from the Stashed side, keep `id.title()` from the Upstream side.

**Files:**
- Modify: `BTAPI/views.py:97-103`

- [ ] **Step 1: Replace the conflict block with the hybrid resolution**

In `BTAPI/views.py`, the current block looks like this:

```python
    new_parent = request.query_params.get('parent')
<<<<<<< Updated upstream
    # dev_id = request.query_params.get('dev')
    report = get_object_or_404(DefectReport, id=id.title())
=======
    dev_id = request.query_params.get('dev')
    report = get_object_or_404(DefectReport, id=id)
>>>>>>> Stashed changes
    
    user = request.user
```

Replace those seven lines (the three Stashed/Upstream marker lines and the four content lines between them) with these two lines:

```python
    dev_id = request.query_params.get('dev')
    report = get_object_or_404(DefectReport, id=id.title())
```

The result around lines 96–100 should read:

```python
    new_parent = request.query_params.get('parent')
    dev_id = request.query_params.get('dev')
    report = get_object_or_404(DefectReport, id=id.title())
    
    user = request.user
```

- [ ] **Step 2: Verify the file imports**

```bash
python3 -c "import BTAPI.views; print('views.py imports cleanly')"
```

Expected: `views.py imports cleanly`. If you see `SyntaxError`, the conflict markers are still present — re-check Step 1. If you see `ModuleNotFoundError: No module named 'django_tenants'`, you skipped pre-flight Step 3.

- [ ] **Step 3: Verify no conflict markers remain anywhere in the repo**

```bash
git grep -n '<<<<<<< \|=======\|>>>>>>> ' -- 'BTAPI/' 'BTConfig/' || echo "no conflict markers"
```

Expected: `no conflict markers`. If the command prints any line, fix that conflict before continuing.

- [ ] **Step 4: Mark the file as resolved and commit**

```bash
git add BTAPI/views.py
git commit -m "fix: resolve merge conflict in patch_update_report

Hybrid resolution: keep dev_id capture from Stashed (referenced later
at line 164) and id.title() lookup from Upstream (consistent with
sibling endpoints that look up TitleCase DefectReport PKs)."
```

Expected: a single new commit on `dev`. `git status` no longer lists `BTAPI/views.py` under "Unmerged paths".

---

## Task 2: Delete the broken `DefectReportTestCase`

`BTAPI/tests.py` contains a single test that calls `ProductOwner.objects.create(...)`, but the `ProductOwner` model was removed (commented out in `BTAPI/models.py`). The test cannot run. Sub-project 2 will replace it with proper APITestCase coverage; for now, delete it so the test runner has a clean slate.

**Files:**
- Modify: `BTAPI/tests.py`

- [ ] **Step 1: Replace the file contents**

Overwrite `BTAPI/tests.py` with:

```python
from django.test import SimpleTestCase

# Classifier tests are added in Task 4.
```

- [ ] **Step 2: Verify the file imports**

```bash
python3 -c "import BTAPI.tests; print('tests.py imports cleanly')"
```

Expected: `tests.py imports cleanly`.

- [ ] **Step 3: Commit**

```bash
git add BTAPI/tests.py
git commit -m "test: remove stale DefectReportTestCase

References the removed ProductOwner model and testerEmail field, so it
cannot run. Replacement APITestCase coverage lands in Sub-project 2."
```

---

## Task 3: Add the test-only settings module

The active `DATABASES` config requires PostgreSQL + `django-tenants`, which isn't running locally. This task adds `BTConfig/settings_test.py` (SQLite in-memory + tenants stripped) so tests can run today without standing up Postgres. See spec §5.

**Files:**
- Create: `BTConfig/settings_test.py`

- [ ] **Step 1: Create the file**

Write `BTConfig/settings_test.py` with these exact contents:

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

- [ ] **Step 2: Verify Django can load the settings**

```bash
python3 manage.py check --settings=BTConfig.settings_test
```

Expected: `System check identified no issues (0 silenced).` If you see warnings about `django_tenants`, recheck the `INSTALLED_APPS` filter line.

- [ ] **Step 3: Verify the test runner discovers zero tests cleanly**

```bash
python3 manage.py test --settings=BTConfig.settings_test BTAPI -v 2
```

Expected: output ends with `Ran 0 tests in 0.000s` and `OK`. (We deleted the only test in Task 2; new tests are added in Task 4.)

- [ ] **Step 4: Commit**

```bash
git add BTConfig/settings_test.py
git commit -m "test: add SQLite-backed test-only settings module

Strips django_tenants from INSTALLED_APPS and MIDDLEWARE so the suite
runs on in-memory SQLite without requiring a local Postgres instance.
Tenant isolation is not exercised here; that needs a second pass once
Sub-project 3 lands."
```

---

## Task 4: Write the failing classifier tests (TDD red)

Write the six-case test class against `BTAPI.metrics.classify_developer_effectiveness`. The module does not exist yet — tests must fail with `ImportError`. This is the TDD "red" step.

**Files:**
- Modify: `BTAPI/tests.py`

- [ ] **Step 1: Add the test class**

Replace the contents of `BTAPI/tests.py` with:

```python
from django.test import SimpleTestCase

from BTAPI.metrics import classify_developer_effectiveness


class ClassifierTests(SimpleTestCase):
    """Cover Sprint 3 §22-24: classify_developer_effectiveness.

    Six cases give full statement coverage and full branch coverage
    of BTAPI/metrics.py.  Boundary cases 4 and 6 pin the strict-`<`
    semantics of the thresholds and are the cases most likely to
    catch a future `<=` regression.
    """

    def test_zero_data_returns_insufficient(self):
        # fixed_count < 20 branch true (case 1)
        self.assertEqual(
            classify_developer_effectiveness(0, 0),
            "Insufficient data",
        )

    def test_just_below_threshold_returns_insufficient(self):
        # fixed_count < 20 branch true (case 2: 19 fixes is still not enough)
        self.assertEqual(
            classify_developer_effectiveness(19, 0),
            "Insufficient data",
        )

    def test_at_threshold_zero_reopened_returns_good(self):
        # fixed_count < 20 false; ratio 0 < 1/32 true (case 3)
        self.assertEqual(
            classify_developer_effectiveness(20, 0),
            "Good",
        )

    def test_ratio_exactly_one_thirty_second_returns_fair(self):
        # ratio == 1/32 -> ratio < 1/32 false; ratio < 1/8 true (case 4)
        self.assertEqual(
            classify_developer_effectiveness(32, 1),
            "Fair",
        )

    def test_ratio_between_thresholds_returns_fair(self):
        # ratio == 3/32 (0.09375) -> Fair (case 5)
        self.assertEqual(
            classify_developer_effectiveness(32, 3),
            "Fair",
        )

    def test_ratio_exactly_one_eighth_returns_poor(self):
        # ratio == 1/8 -> ratio < 1/8 false -> Poor (case 6)
        self.assertEqual(
            classify_developer_effectiveness(32, 4),
            "Poor",
        )
```

- [ ] **Step 2: Run the tests and verify they fail with ImportError**

```bash
python3 manage.py test --settings=BTConfig.settings_test BTAPI.tests -v 2
```

Expected: collection fails at the `from BTAPI.metrics import classify_developer_effectiveness` line. You should see `ModuleNotFoundError: No module named 'BTAPI.metrics'` in the output. This is the red step — failure is correct here. Do not commit yet.

---

## Task 5: Implement the classifier (TDD green)

Create `BTAPI/metrics.py` with the pure-function classifier exactly as specified. This is the TDD "green" step.

**Files:**
- Create: `BTAPI/metrics.py`

- [ ] **Step 1: Create the module**

Write `BTAPI/metrics.py` with these exact contents:

```python
def classify_developer_effectiveness(fixed_count: int, reopened_count: int) -> str:
    if fixed_count < 20:
        return "Insufficient data"
    ratio = reopened_count / fixed_count
    if ratio < 1 / 32:
        return "Good"
    if ratio < 1 / 8:
        return "Fair"
    return "Poor"
```

Note on the literals: `1/32` and `1/8` are reciprocals of powers of two and round-trip exactly in IEEE 754 (`0.03125` and `0.125`), so the boundary tests in Task 4 are deterministic.

- [ ] **Step 2: Run the tests and verify all six pass**

```bash
python3 manage.py test --settings=BTConfig.settings_test BTAPI.tests -v 2
```

Expected: `Ran 6 tests in 0.00Xs` and `OK`. All six test method names appear in the output, each marked `... ok`.

- [ ] **Step 3: Commit the test class together with the implementation**

```bash
git add BTAPI/metrics.py BTAPI/tests.py
git commit -m "feat(metrics): extract developer-effectiveness classifier

Pure function classify_developer_effectiveness(fixed, reopened) -> str
implementing Sprint 3 §22-24.  Six SimpleTestCase cases cover every
statement and both directions of every branch, with cases 4 and 6
pinning the strict-< boundary semantics."
```

---

## Task 6: Refactor the view to use the extracted classifier

Replace the inline classification logic in `get_developer_metric` with a call to the new module function. Behaviour must stay identical — same URL, same permission, same `id.title()` lookup, same response shape.

**Files:**
- Modify: `BTAPI/views.py:70-87`

- [ ] **Step 1: Add the import near the top of `views.py`**

Find the existing imports block (lines 1–9). Add this line after `from .utils import *`:

```python
from .metrics import classify_developer_effectiveness
```

The import block should now end with:

```python
from .utils import *
from .metrics import classify_developer_effectiveness
```

- [ ] **Step 2: Replace the `get_developer_metric` view body**

The current view at `BTAPI/views.py:68–87` is:

```python
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_developer_metric(request, id):
    developer = get_object_or_404(Developer, user__username=id.title())

    fixed_count = developer.fixedCount
    reopened_count = developer.reopenedCount

    report = "Insufficient data"
    if fixed_count >= 20:
        ratio = reopened_count / fixed_count
        match ratio:
            case val if val < (1/32):
                report = "Good"
            case val if val < (1/8):
                report = "Fair"
            case _:
                report = "Poor"

    return Response({"report": report})
```

Replace it with:

```python
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_developer_metric(request, id):
    developer = get_object_or_404(Developer, user__username=id.title())
    report = classify_developer_effectiveness(
        developer.fixedCount, developer.reopenedCount
    )
    return Response({"report": report})
```

- [ ] **Step 3: Verify the file still imports**

```bash
python3 -c "import BTAPI.views; print('views.py imports cleanly')"
```

Expected: `views.py imports cleanly`.

- [ ] **Step 4: Re-run the test suite to confirm nothing else broke**

```bash
python3 manage.py test --settings=BTConfig.settings_test BTAPI -v 2
```

Expected: `Ran 6 tests in 0.00Xs` and `OK`.

- [ ] **Step 5: Commit**

```bash
git add BTAPI/views.py
git commit -m "refactor(views): use extracted classifier in get_developer_metric

Behaviour-preserving: same URL, same IsAuthenticated permission, same
id.title() lookup, same {\"report\": ...} response shape.  The inline
match/case block is replaced by a call to classify_developer_effectiveness
so coverage measurement is decoupled from the HTTP layer."
```

---

## Task 7: Add `coverage.py` to `requirements.txt` and install it

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Append `coverage==7.6.10` to `requirements.txt`**

Add this single line at the end of `requirements.txt` (preserve all existing lines):

```
coverage==7.6.10
```

- [ ] **Step 2: Install it in the active virtualenv**

```bash
pip install coverage==7.6.10
coverage --version
```

Expected: `coverage --version` prints `Coverage.py, version 7.6.10 ...`.

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "chore(deps): add coverage 7.6.10 for Sprint 3 §25 coverage rubric"
```

---

## Task 8: Add `.coveragerc`

**Files:**
- Create: `.coveragerc`

- [ ] **Step 1: Create the file at the repo root**

Write `.coveragerc` with these exact contents:

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

`branch = True` is what enables branch-coverage measurement (Sprint 3 §25). `source = BTAPI` keeps the percentage scoped to app code; Django/DRF internals are excluded automatically. Migrations, tests, and trivial config files are omitted so the headline number reflects production code.

- [ ] **Step 2: Commit**

```bash
git add .coveragerc
git commit -m "chore: add .coveragerc with branch coverage scoped to BTAPI"
```

---

## Task 9: Verify 100% statement and branch coverage of the classifier

Run the coverage tools and confirm `BTAPI/metrics.py` shows 100% on both metrics. This is the Sprint 3 §25 grading hook.

- [ ] **Step 1: Run the test suite under `coverage`**

```bash
coverage run --rcfile=.coveragerc manage.py test --settings=BTConfig.settings_test BTAPI
```

Expected: `Ran 6 tests in 0.00Xs` and `OK`. A `.coverage` file appears in the repo root.

- [ ] **Step 2: Show the classifier-only coverage report**

```bash
coverage report -m --include='BTAPI/metrics.py'
```

Expected output shape (the percentages must be exactly 100% and 100%):

```
Name               Stmts   Miss Branch BrPart   Cover   Missing
---------------------------------------------------------------
BTAPI/metrics.py       6      0      6      0  100.0%
---------------------------------------------------------------
TOTAL                  6      0      6      0  100.0%
```

If `Cover` is below 100% or `Missing` is non-empty, you have a gap. Re-read Task 4 — one of the six cases is missing or wrong.

- [ ] **Step 3: Show the full report (informational; not graded)**

```bash
coverage report -m
```

Expected: a multi-line table covering several `BTAPI/*` files. Most will have <100% coverage — that is fine. Only `BTAPI/metrics.py` is required to hit 100%.

- [ ] **Step 4: Generate the HTML report (optional, for the demo)**

```bash
coverage html
```

Expected: an `htmlcov/` directory appears with `index.html`. Open it in a browser if you want to inspect line-by-line coverage.

- [ ] **Step 5: Add `htmlcov/` and `.coverage` to `.gitignore` if not already there**

```bash
grep -E '^(htmlcov/?|\.coverage)$' .gitignore || cat <<'EOF' >> .gitignore

# coverage.py outputs
.coverage
htmlcov/
EOF
```

Expected: either no output (already ignored) or two lines appended.

- [ ] **Step 6: Commit the `.gitignore` update if it changed**

```bash
git add .gitignore
git diff --cached --quiet .gitignore || git commit -m "chore: gitignore coverage.py outputs"
```

Expected: either a new commit, or no commit because `.gitignore` was already up to date.

---

## Task 10: Document Testing & Coverage in README

Add a new section to `README.md` so the grader (and future contributors) know how to reproduce the coverage result.

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Read the current README to find a sensible insertion point**

```bash
grep -n '^##' README.md
```

Identify the heading **before** which the new "Testing & Coverage" section should be inserted (typically after a "Setup" or "Run" section, before any "License" or "Contributors" section).

- [ ] **Step 2: Insert the new section**

Insert this block in the README at the chosen location (preserve all surrounding content):

````markdown
## Testing & Coverage

The active settings module (`BTConfig/settings`) targets PostgreSQL with
`django-tenants`. For fast local test runs without standing up Postgres,
this project ships a SQLite-backed test-only settings module
(`BTConfig.settings_test`) that strips the tenants layer.

> ⚠️  Tests under `settings_test` do **not** exercise tenant isolation.
> A second pass under the real Postgres + tenants configuration is
> required once Sub-project 3 (multi-tenancy) lands.

### Run the test suite

```bash
python3 manage.py test --settings=BTConfig.settings_test BTAPI
```

### Measure statement and branch coverage

The Sprint 3 §25 rubric requires full statement and full branch coverage
of the developer-effectiveness classifier (`BTAPI/metrics.py`).

```bash
# 1. Run the suite under coverage
coverage run --rcfile=.coveragerc manage.py test \
    --settings=BTConfig.settings_test BTAPI

# 2. Whole-app report (informational)
coverage report -m

# 3. Classifier-only report (the §25 grading hook)
coverage report -m --include='BTAPI/metrics.py'

# 4. Optional HTML drill-down
coverage html  # writes htmlcov/index.html
```

Step 3 must show `100.0%` under `Cover` for `BTAPI/metrics.py` with an
empty `Missing` column. The six cases in `BTAPI/tests.py::ClassifierTests`
are what produce that result.
````

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs(readme): add Testing & Coverage section"
```

---

## Final verification

- [ ] **Step 1: Confirm everything still runs end-to-end**

```bash
python3 -c "import BTAPI.views, BTAPI.metrics, BTAPI.tests; print('all modules import')"
python3 manage.py check --settings=BTConfig.settings_test
coverage run --rcfile=.coveragerc manage.py test --settings=BTConfig.settings_test BTAPI
coverage report -m --include='BTAPI/metrics.py'
```

Expected:
- `all modules import`
- `System check identified no issues (0 silenced).`
- `Ran 6 tests in 0.00Xs` and `OK`
- `BTAPI/metrics.py` line shows `100.0%` Cover, empty Missing

- [ ] **Step 2: Confirm git history**

```bash
git log --oneline -15
```

Expected (most recent first, approximately):

```
docs(readme): add Testing & Coverage section
chore: gitignore coverage.py outputs            (may be absent if no change)
chore: add .coveragerc with branch coverage scoped to BTAPI
chore(deps): add coverage 7.6.10 for Sprint 3 §25 coverage rubric
refactor(views): use extracted classifier in get_developer_metric
feat(metrics): extract developer-effectiveness classifier
test: add SQLite-backed test-only settings module
test: remove stale DefectReportTestCase
fix: resolve merge conflict in patch_update_report
docs: add Sprint 3 sub-project 1 design (developer effectiveness metric + coverage)
... (older commits)
```

- [ ] **Step 3: Confirm no merge conflict markers anywhere**

```bash
git grep -n '<<<<<<< \|=======\|>>>>>>> ' || echo "clean"
```

Expected: `clean`.

---

## Acceptance criteria (from the spec)

The plan is complete when all five spec acceptance criteria hold:

1. ✅ `python3 -c "import BTAPI.views"` returns no error → verified in Task 1 Step 2 and Task 6 Step 3.
2. ✅ `python3 manage.py test --settings=BTConfig.settings_test BTAPI` reports six tests passing in `ClassifierTests` → verified in Task 5 Step 2 and Task 6 Step 4.
3. ✅ `coverage report -m --include='BTAPI/metrics.py'` shows 100% statement and 100% branch coverage → verified in Task 9 Step 2.
4. ✅ `GET /api/metric/<username>/` continues to return `{"report": "<classification>"}` identical to today's behaviour → preserved by the behaviour-preserving refactor in Task 6.
5. ✅ README documents the test and coverage commands → done in Task 10.

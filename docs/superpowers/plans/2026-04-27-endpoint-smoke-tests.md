# Endpoint Smoke Tests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver Sprint 3 sub-project 2 — one representative happy-path test for each of the 10 BetaTrax API endpoint methods, using DRF's `APIClient`, with shared `setUpTestData` fixture and an in-memory email backend so the suite has no filesystem side effects.

**Architecture:** All new test code goes into the existing `BTAPI/tests.py` as a second class `EndpointSmokeTests(APITestCase)` alongside the existing `ClassifierTests`. One settings-only change adds the locmem email backend to `BTConfig/settings_test.py`. No `BTAPI/views.py` changes — the spec deliberately works around four known view-layer bugs by choosing fixture identifiers and request paths that exercise the existing buggy code's happy paths.

**Tech Stack:** Django 6.0.3, Django REST Framework 3.17.1, `rest_framework.test.APITestCase`, JWT via `simplejwt`, SQLite in-memory (test runtime).

**Design spec:** `docs/superpowers/specs/2026-04-27-endpoint-smoke-tests-design.md`

**Note on TDD:** Unlike sub-project 1, this is not a red-green-refactor cycle. We are testing pre-existing code, so each test should pass on first run. If a test fails, that is a real signal — stop and investigate before forcing the test to pass.

---

## Pre-flight

- [ ] **Pre-flight Step 1: Confirm baseline from sub-project 1 still passes**

```bash
cd /Users/wangyamyuk13/Documents/GitHub/BetaTrax
source venv/bin/activate
python3 manage.py test --settings=BTConfig.settings_test BTAPI -v 2 2>&1 | tail -10
```

Expected: `Ran 6 tests in 0.00Xs` and `OK` — six classifier tests from sub-project 1.

- [ ] **Pre-flight Step 2: Capture the baseline `email/` directory state**

```bash
ls email/ 2>/dev/null | wc -l
```

Note the count. The final verification compares this against the post-test count to prove acceptance criterion #4 (no filesystem side effects).

---

## Task 1: Add the locmem email backend to `settings_test.py`

The default file-based email backend writes `.eml` files into `email/` whenever a view fires a notification. Tests must not pollute the working tree, so override the backend to in-memory.

**Files:**
- Modify: `BTConfig/settings_test.py`

- [ ] **Step 1: Append the email backend override**

`BTConfig/settings_test.py` currently ends with:

```python
MIDDLEWARE = [m for m in MIDDLEWARE if 'django_tenants' not in m]
```

Append one line:

```python
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
```

The full file should now read:

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
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
```

- [ ] **Step 2: Verify settings still load**

```bash
python3 manage.py check --settings=BTConfig.settings_test
```

Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 3: Verify existing tests still pass under the new backend**

```bash
python3 manage.py test --settings=BTConfig.settings_test BTAPI -v 2 2>&1 | tail -5
```

Expected: `Ran 6 tests in 0.00Xs` and `OK`.

- [ ] **Step 4: Commit**

```bash
git commit --only BTConfig/settings_test.py -m "test: use locmem email backend in test settings

Prevents notification emails from creating .eml files in email/
during test runs."
```

---

## Task 2: Add imports and `EndpointSmokeTests` class with `setUpTestData`

Set up the fixture without any tests yet. This task verifies that the fixture itself constructs cleanly (group/user/product/defect creation, FK relationships, the `Developer.clean()` validator).

**Files:**
- Modify: `BTAPI/tests.py`

- [ ] **Step 1: Replace the contents of `BTAPI/tests.py`**

Overwrite the entire file with:

```python
from django.contrib.auth.models import Group, User
from django.test import SimpleTestCase
from rest_framework.test import APITestCase

from BTAPI.metrics import classify_developer_effectiveness
from BTAPI.models import Comment, DefectReport, Developer, Product


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


class EndpointSmokeTests(APITestCase):
    """Sprint 3 §38: one representative happy-path test per endpoint
    method.

    Fixture identifiers are TitleCase ('Tester', 'Dev', 'Po', 'Def001',
    'Prod001') so that endpoint-side `.title()` lookups are no-ops
    -- this sidesteps a known case-fragility bug without changing
    the views.  Tests added in subsequent tasks.
    """

    @classmethod
    def setUpTestData(cls):
        user_group = Group.objects.create(name='User')
        dev_group = Group.objects.create(name='Developer')
        owner_group = Group.objects.create(name='Owner')

        cls.tester = User.objects.create_user(
            username='Tester', password='pw', email='tester@example.com')
        cls.tester.groups.add(user_group)

        cls.dev = User.objects.create_user(
            username='Dev', password='pw', email='dev@example.com')
        cls.dev.groups.add(dev_group)

        cls.po = User.objects.create_user(
            username='Po', password='pw', email='po@example.com')
        cls.po.groups.add(owner_group)

        cls.dev_profile = Developer.objects.create(
            user=cls.dev, fixedCount=0, reopenedCount=0)

        cls.product = Product.objects.create(
            id='Prod001',
            displayName='Test Product',
            description='desc',
            currentVersion='1.0',
            isActiveBeta=True,
            ownerId=cls.po,
            devId=cls.dev,
        )

        cls.defect = DefectReport.objects.create(
            id='Def001',
            productId=cls.product,
            productVersion='1.0',
            title='Seed defect',
            description='desc',
            reproductionSteps='steps',
            testerId=cls.tester,
            status=DefectReport.Status.NEW,
            assignedToId=cls.dev,
        )
```

- [ ] **Step 2: Verify the file imports and the class fixture builds**

```bash
python3 manage.py test --settings=BTConfig.settings_test BTAPI -v 2 2>&1 | tail -10
```

Expected: `Ran 6 tests` and `OK`. The `EndpointSmokeTests` class is discovered but contains no test methods, so the count stays at 6. If the fixture has a problem (e.g. `Developer.clean()` rejection, FK violation), Django's test loader will surface the error here — stop and investigate.

- [ ] **Step 3: Commit**

```bash
git commit --only BTAPI/tests.py -m "test: add EndpointSmokeTests class with setUpTestData fixture

Three users (Tester/Dev/Po) in their respective groups, one Developer
profile, one Product, one seed DefectReport in 'New' status.
Fixture identifiers are TitleCase so endpoint-side .title() lookups
are no-ops."
```

---

## Task 3: Add the two token endpoint tests (#1, #2)

These two tests use the real JWT flow (no `force_authenticate`) so they exercise `TokenObtainPairSerializer` and the JWT chain end-to-end.

**Files:**
- Modify: `BTAPI/tests.py`

- [ ] **Step 1: Append the two test methods to `EndpointSmokeTests`**

Add these methods to the end of the `EndpointSmokeTests` class (after `setUpTestData`):

```python
    def test_post_token_returns_access_and_refresh(self):
        """#1: POST /api/token/ — JWT obtain."""
        response = self.client.post(
            '/api/token/',
            {'username': 'Tester', 'password': 'pw'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_post_token_refresh_returns_new_access(self):
        """#2: POST /api/token/refresh/ — JWT refresh."""
        obtain = self.client.post(
            '/api/token/',
            {'username': 'Tester', 'password': 'pw'},
            format='json',
        )
        refresh_token = obtain.data['refresh']

        response = self.client.post(
            '/api/token/refresh/',
            {'refresh': refresh_token},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)
```

- [ ] **Step 2: Run only these two new tests to verify they pass**

```bash
python3 manage.py test --settings=BTConfig.settings_test \
    BTAPI.tests.EndpointSmokeTests.test_post_token_returns_access_and_refresh \
    BTAPI.tests.EndpointSmokeTests.test_post_token_refresh_returns_new_access \
    -v 2 2>&1 | tail -10
```

Expected: `Ran 2 tests in 0.0XXs` and `OK`.

- [ ] **Step 3: Run the full suite to verify nothing else broke**

```bash
python3 manage.py test --settings=BTConfig.settings_test BTAPI -v 2 2>&1 | tail -5
```

Expected: `Ran 8 tests in 0.0XXs` and `OK` (6 classifier + 2 token).

- [ ] **Step 4: Commit**

```bash
git commit --only BTAPI/tests.py -m "test(endpoints): add token obtain and refresh smoke tests"
```

---

## Task 4: Add the four GET endpoint tests (#4, #5, #6, #10)

All four are reads using `force_authenticate` to skip the JWT chain (which is already covered by Task 3's tests).

**Files:**
- Modify: `BTAPI/tests.py`

- [ ] **Step 1: Append the four GET test methods to `EndpointSmokeTests`**

Add to the end of the class:

```python
    def test_get_reports_by_status_returns_list(self):
        """#4: GET /api/reports/<status>/ — list reports filtered by status."""
        self.client.force_authenticate(user=self.tester)
        response = self.client.get('/api/reports/NEW/')
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)
        ids = [item['id'] for item in response.data]
        self.assertIn('Def001', ids)

    def test_get_assigned_defects_returns_ok(self):
        """#5: GET /api/reports/assigned/<dev.pk>/ — developer's ASSIGNED tasks.

        The seed defect is in 'New' state (not 'Assigned'), so the endpoint
        returns the 'No assigned reports' message.  We pass dev.pk as the
        URL parameter to sidestep the known bug at views.py:55 that does
        `assignedToId=id.title()` against an FK column.
        """
        self.client.force_authenticate(user=self.dev)
        response = self.client.get(f'/api/reports/assigned/{self.dev.pk}/')
        self.assertEqual(response.status_code, 200)

    def test_get_full_report_returns_defect(self):
        """#6: GET /api/defect/<id>/ — full defect detail.

        Lowercase URL parameter ('def001') deliberately exercises the
        existing `.title()` lookup convention.
        """
        self.client.force_authenticate(user=self.tester)
        response = self.client.get('/api/defect/def001/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['id'], 'Def001')

    def test_get_developer_metric_returns_classification(self):
        """#10: GET /api/metric/<id>/ — developer effectiveness classification.

        Lowercase URL parameter ('dev') deliberately exercises the
        `.title()` lookup convention.  fixedCount is 0 so the
        classifier returns 'Insufficient data'.
        """
        self.client.force_authenticate(user=self.dev)
        response = self.client.get('/api/metric/dev/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['report'], 'Insufficient data')
```

- [ ] **Step 2: Run only these four new tests to verify they pass**

```bash
python3 manage.py test --settings=BTConfig.settings_test \
    BTAPI.tests.EndpointSmokeTests.test_get_reports_by_status_returns_list \
    BTAPI.tests.EndpointSmokeTests.test_get_assigned_defects_returns_ok \
    BTAPI.tests.EndpointSmokeTests.test_get_full_report_returns_defect \
    BTAPI.tests.EndpointSmokeTests.test_get_developer_metric_returns_classification \
    -v 2 2>&1 | tail -15
```

Expected: `Ran 4 tests in 0.0XXs` and `OK`.

- [ ] **Step 3: Run the full suite to verify nothing else broke**

```bash
python3 manage.py test --settings=BTConfig.settings_test BTAPI -v 2 2>&1 | tail -5
```

Expected: `Ran 12 tests in 0.0XXs` and `OK` (6 classifier + 2 token + 4 GET).

- [ ] **Step 4: Commit**

```bash
git commit --only BTAPI/tests.py -m "test(endpoints): add GET smoke tests for reports/assigned/full/metric"
```

---

## Task 5: Add the four POST/PATCH endpoint tests (#3, #7, #8, #9)

These four tests mutate state. Each runs in its own transaction that rolls back, so order independence and seed reuse are preserved.

**Files:**
- Modify: `BTAPI/tests.py`

- [ ] **Step 1: Append the four mutating-endpoint test methods to `EndpointSmokeTests`**

Add to the end of the class:

```python
    def test_post_new_report_creates_defect(self):
        """#3: POST /api/defect/ — submit a new defect report."""
        self.client.force_authenticate(user=self.tester)
        response = self.client.post(
            '/api/defect/',
            {
                'id': 'Def002',
                'productId': 'Prod001',
                'productVersion': '1.0',
                'title': 'Crashes on startup',
                'description': 'App quits immediately.',
                'reproductionSteps': '1. Open app',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['status'], 'New')

    def test_patch_update_report_new_to_open(self):
        """#7: PATCH /api/update/<id>/?status=Open — owner moves New -> Open.

        Simplest workflow transition; avoids the duplicate-link branches
        and the raw-vs-titled comparison bug at views.py:101.
        """
        self.client.force_authenticate(user=self.po)
        response = self.client.patch('/api/update/def001/?status=Open')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'Open')

    def test_post_comment_creates_comment(self):
        """#8: POST /api/comment/<id>/ — post a comment on a defect.

        Comment.id is a manually-assigned CharField, so the body must
        include a unique 'id' value.
        """
        self.client.force_authenticate(user=self.tester)
        response = self.client.post(
            '/api/comment/def001/',
            {'id': 'Com001', 'content': 'I see this too.'},
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['content'], 'I see this too.')

    def test_post_new_product_creates_product(self):
        """#9: POST /api/product/ — register a new product."""
        self.client.force_authenticate(user=self.po)
        response = self.client.post(
            '/api/product/',
            {
                'id': 'Prod002',
                'displayName': 'BetaTrax Mobile',
                'description': 'Mobile companion app.',
                'currentVersion': '0.1',
                'isActiveBeta': True,
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['id'], 'Prod002')
```

- [ ] **Step 2: Run only these four new tests to verify they pass**

```bash
python3 manage.py test --settings=BTConfig.settings_test \
    BTAPI.tests.EndpointSmokeTests.test_post_new_report_creates_defect \
    BTAPI.tests.EndpointSmokeTests.test_patch_update_report_new_to_open \
    BTAPI.tests.EndpointSmokeTests.test_post_comment_creates_comment \
    BTAPI.tests.EndpointSmokeTests.test_post_new_product_creates_product \
    -v 2 2>&1 | tail -15
```

Expected: `Ran 4 tests in 0.0XXs` and `OK`.

- [ ] **Step 3: Run the full suite to verify all 16 tests pass together**

```bash
python3 manage.py test --settings=BTConfig.settings_test BTAPI -v 2 2>&1 | tail -25
```

Expected: `Ran 16 tests in 0.0XXs` and `OK`. All test method names appear in the output.

- [ ] **Step 4: Commit**

```bash
git commit --only BTAPI/tests.py -m "test(endpoints): add POST/PATCH smoke tests for defect/update/comment/product

Completes Sprint 3 §38 -- one representative happy-path test per
endpoint method, 10 endpoints total."
```

---

## Task 6: Final verification

- [ ] **Step 1: Confirm all 16 tests still pass**

```bash
python3 manage.py test --settings=BTConfig.settings_test BTAPI -v 2 2>&1 | tail -25
```

Expected: `Ran 16 tests in 0.0XXs` and `OK`.

- [ ] **Step 2: Confirm classifier coverage is still 100%/100%**

```bash
coverage run --rcfile=.coveragerc manage.py test --settings=BTConfig.settings_test BTAPI 2>&1 | tail -5
coverage report -m --include='BTAPI/metrics.py'
```

Expected: tests pass; `BTAPI/metrics.py` shows `100.0%` Cover, empty Missing column.

- [ ] **Step 3: Confirm no email files were created during the test run**

```bash
ls email/ 2>/dev/null | wc -l
```

Compare against the count captured in pre-flight Step 2 — they should be identical.

- [ ] **Step 4: Show whole-app coverage as informational (not graded)**

```bash
coverage report -m
```

Expected: `BTAPI/views.py` Cover line is significantly higher than today's 14.2% baseline (likely 60–80%). The exact number is informational only.

- [ ] **Step 5: Confirm git history**

```bash
git log --oneline -10
```

Expected (most recent first):

```
test(endpoints): add POST/PATCH smoke tests for defect/update/comment/product
test(endpoints): add GET smoke tests for reports/assigned/full/metric
test(endpoints): add token obtain and refresh smoke tests
test: add EndpointSmokeTests class with setUpTestData fixture
test: use locmem email backend in test settings
docs: add Sprint 3 sub-project 2 design (endpoint smoke tests)
... (sub-project 1 commits)
```

- [ ] **Step 6: Confirm working tree is clean**

```bash
git status --short
```

Expected: empty output.

---

## Acceptance criteria (from the spec)

1. ✅ `python3 manage.py test --settings=BTConfig.settings_test BTAPI` reports **16 tests passing** → verified Tasks 5, 6.
2. ✅ Every endpoint method in spec §4 has exactly one test in `EndpointSmokeTests` that asserts both the success status code and one response-body invariant → verified by inspection of the 10 added test methods (#1–#10 in spec §8).
3. ✅ `coverage report -m --include='BTAPI/metrics.py'` still shows `100.0%` → verified Task 6 Step 2.
4. ✅ No `.eml` files written during the run → verified Task 6 Step 3.
5. ✅ `BTAPI/views.py` coverage noticeably higher than today's 14.2% → verified Task 6 Step 4.

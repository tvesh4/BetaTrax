# BetaTrax Sprint 3 — Sub-project 2: Endpoint Smoke Tests

**Date:** 2026-04-27
**Author:** Claude (brainstormed with dalight-luckyw)
**Status:** Approved for planning
**Scope:** Sub-project 2 of 4 in Sprint 3. Delivers Sprint 3 §38 "a successful execution of each method available on each endpoint", using DRF's `APIClient`. Adds 10 happy-path tests to `BTAPI/tests.py` alongside the existing `ClassifierTests`.

This spec depends on Sub-project 1 having landed: it relies on `BTConfig/settings_test.py`, the test-only SQLite settings module, and the `coverage.py` wiring already in place.

## 1. Background

Sprint 3 §38 reads: *"a successful execution of each method available on each endpoint. You may do this either by using the DRF's APIClient to execute requests against endpoints, or by building requests with APIRequestFactory and calling the relevant views directly. We require only a single test for each endpoint method (again, each is just a representative case)."*

The test runner and infrastructure landed in Sub-project 1. `BTAPI/tests.py` currently contains only `ClassifierTests` (6 cases against the pure classifier function). This sub-project adds an `EndpointSmokeTests` class that drives every endpoint through `APIClient`, asserting 2xx + one response-body invariant per test.

## 2. Goals

1. One representative happy-path test for each of the 10 endpoint methods listed in §3.
2. Use `APIClient` (the higher-fidelity option from §38) so URL routing, auth, and permission classes are exercised end-to-end.
3. No filesystem side effects during test runs (override the email backend to in-memory).
4. Keep the existing 100% statement+branch coverage on `BTAPI/metrics.py` from Sub-project 1.
5. Bring `BTAPI/views.py` coverage from today's 14.2% baseline up to roughly 60–80% as a side effect (informational; not graded).

## 3. Non-goals

- Negative tests (auth failures, role failures, 400/403/404 paths).
- Coverage of `patch_update_report` workflow branches beyond the single chosen New → Open path.
- Verifying `fixedCount` / `reopenedCount` are correctly maintained end-to-end. (Belongs to a future view-layer cleanup; not graded for Sprint 3.)
- Tightening permissions, fixing the `.title()` lookup convention, or any other view-layer bug — see §11 for the full list of known issues we explicitly leave in place.
- Multi-tenancy completion (Sub-project 3) and API documentation (Sub-project 4).

## 4. Endpoint inventory

The 10 methods, all under the `/api/` prefix:

| # | Method | Path | View | Permission |
|---|---|---|---|---|
| 1 | POST | `/api/token/` | `TokenObtainPairView` (built-in) | none |
| 2 | POST | `/api/token/refresh/` | `TokenRefreshView` (built-in) | none |
| 3 | POST | `/api/defect/` | `post_new_report` | `IsAuthenticated` |
| 4 | GET | `/api/reports/<status>/` | `get_reports` | `IsAuthenticated` |
| 5 | GET | `/api/reports/assigned/<id>/` | `get_assigned_defects` | `IsDeveloper \| IsOwner` |
| 6 | GET | `/api/defect/<id>/` | `get_full_report` | `IsAuthenticated` |
| 7 | PATCH | `/api/update/<id>/` | `patch_update_report` | `IsUser \| IsOwner \| IsDeveloper` |
| 8 | POST | `/api/comment/<id>/` | `post_comment` | `IsAuthenticated` |
| 9 | POST | `/api/product/` | `post_new_product` | `IsOwner \| IsDeveloper` |
| 10 | GET | `/api/metric/<id>/` | `get_developer_metric` | `IsAuthenticated` |

## 5. Settings change

Add one line to `BTConfig/settings_test.py`:

```python
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
```

Several endpoints fire notification emails through `BTAPI/utils.py` (e.g., `send_status_update_email`). Without this override the tests would write `.eml` files into the `email/` directory on every run. The `locmem` backend stores sent messages in `django.core.mail.outbox` (in memory) for the duration of the test process and discards them — no filesystem effect.

## 6. Test fixture (`setUpTestData`)

A class-level fixture creates the world once per test class. Django's per-test transaction wraps each method, so any mutations a test makes are rolled back before the next test runs. The fixture is therefore deterministic and independent of test ordering.

```python
@classmethod
def setUpTestData(cls):
    # Groups (CLAUDE.md says they normally come from groups.json fixture,
    # but for tests we create them directly to avoid fixture-loading order
    # issues with django-tenants stripped from INSTALLED_APPS).
    user_group = Group.objects.create(name='User')
    dev_group = Group.objects.create(name='Developer')
    owner_group = Group.objects.create(name='Owner')

    # Users.  Usernames are TitleCase so that endpoint-side `.title()`
    # lookups are no-ops — sidesteps the known case bug (§11) without
    # changing the view.
    cls.tester = User.objects.create_user(
        username='Tester', password='pw', email='tester@example.com')
    cls.tester.groups.add(user_group)

    cls.dev = User.objects.create_user(
        username='Dev', password='pw', email='dev@example.com')
    cls.dev.groups.add(dev_group)

    cls.po = User.objects.create_user(
        username='Po', password='pw', email='po@example.com')
    cls.po.groups.add(owner_group)

    # Developer profile.  Developer.clean() requires the user to be in
    # the 'Developer' group, so this must come after groups.add() above.
    cls.dev_profile = Developer.objects.create(
        user=cls.dev, fixedCount=0, reopenedCount=0)

    # Product.  ownerId and devId are FKs to AUTH_USER_MODEL.
    cls.product = Product.objects.create(
        id='Prod001',
        displayName='Test Product',
        description='desc',
        currentVersion='1.0',
        isActiveBeta=True,
        ownerId=cls.po,
        devId=cls.dev,
    )

    # Seed defect in 'New' status, assigned to dev.
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

## 7. Auth strategy

Two patterns inside the same test class:

- **Token endpoints (#1, #2)** use the real flow: `self.client.post('/api/token/', {...})`. This exercises `TokenObtainPairSerializer` and the JWT chain end-to-end.
- **All other endpoints (#3–#10)** use `self.client.force_authenticate(user=cls.actor)`. This bypasses the JWT verification step but still runs every permission class, because permission classes inspect `request.user.groups`. Faster and avoids per-test token bookkeeping.

`force_authenticate` is reset between tests automatically by `APITestCase`.

## 8. The 10 tests

Each test method is named after the endpoint method it covers. Each asserts the success status code and one obvious invariant from the response body.

| # | Test method | Acts as | Request | Asserts |
|---|---|---|---|---|
| 1 | `test_post_token_returns_access_and_refresh` | (none) | `POST /api/token/` body `{'username':'Tester','password':'pw'}` | `status_code == 200`; both `'access'` and `'refresh'` in `response.data` |
| 2 | `test_post_token_refresh_returns_new_access` | (none) | first POST `/api/token/` to get `refresh`, then POST `/api/token/refresh/` body `{'refresh': <token>}` | `status_code == 200`; `'access'` in `response.data` |
| 3 | `test_post_new_report_creates_defect` | tester | `POST /api/defect/` body with `id='Def002'`, productId=`'Prod001'`, etc. | `status_code == 201`; `response.data['status'] == 'New'` |
| 4 | `test_get_reports_by_status_returns_list` | tester | `GET /api/reports/NEW/` | `status_code == 200`; response is a list and contains an entry with `id == 'Def001'` |
| 5 | `test_get_assigned_defects_returns_ok` | dev | `GET /api/reports/assigned/<dev.pk>/` | `status_code == 200`. Body is the "No assigned reports for this developer" message because the seed defect is `New`, not `Assigned`. The endpoint's bug (filtering by stringified pk instead of username) is sidestepped by using the pk in the URL |
| 6 | `test_get_full_report_returns_defect` | tester | `GET /api/defect/def001/` (lowercase deliberately, exercises the `.title()` lookup) | `status_code == 200`; `response.data['id'] == 'Def001'` |
| 7 | `test_patch_update_report_new_to_open` | po | `PATCH /api/update/def001/?status=Open` | `status_code == 200`; `response.data['status'] == 'Open'` |
| 8 | `test_post_comment_creates_comment` | tester | `POST /api/comment/def001/` body `{'id':'Com001','content':'hello'}` | `status_code == 201`; `response.data['content'] == 'hello'` |
| 9 | `test_post_new_product_creates_product` | po | `POST /api/product/` body `{'id':'Prod002','displayName':'X','description':'y','currentVersion':'1.0','isActiveBeta':True}` | `status_code == 201`; `response.data['id'] == 'Prod002'` |
| 10 | `test_get_developer_metric_returns_classification` | dev | `GET /api/metric/dev/` (lowercase exercises `.title()`) | `status_code == 200`; `response.data['report'] == 'Insufficient data'` (counters are 0) |

**Choice notes:**

- Test #4 uses `NEW` because the seed defect is in NEW state — gives a non-empty list assertion. The full set of valid statuses (NEW/OPEN/ASSIGNED/FIXED/RESOLVED/REOPENED/CLOSED/ALL) is exercised structurally by reading any one of them; Sprint 3 §38 says one test per endpoint method, not one per status branch.
- Test #5 uses `dev.pk` (an int) in the URL because `get_assigned_defects` does `assignedToId=id.title()` against an FK, which Django coerces to int matching. Using a username would silently match nothing.
- Test #7 chooses New → Open because it is the smallest workflow transition, requires no parent-link setup, and avoids the `new_status in ('Duplicate', 'Rejected')` raw-string comparison bug at `views.py:101`.
- Tests #6 and #10 use lowercase URL parameters (`def001`, `dev`) on purpose — they assert the existing `.title()` lookup behaviour works for the TitleCase fixtures.

## 9. File layout

Add the new class to the existing `BTAPI/tests.py`. After this sub-project the file will contain two test classes:

- `ClassifierTests(SimpleTestCase)` — 6 cases (existing).
- `EndpointSmokeTests(APITestCase)` — 10 cases (new).

16 tests total. A separate `tests/` package would be over-engineered at this size and would not improve discoverability.

New imports at the top of `tests.py`:

```python
from django.contrib.auth.models import Group, User
from rest_framework.test import APITestCase

from BTAPI.models import Comment, DefectReport, Developer, Product
```

## 10. Acceptance criteria

1. `python3 manage.py test --settings=BTConfig.settings_test BTAPI` reports **16 tests passing** (6 from `ClassifierTests` + 10 from `EndpointSmokeTests`).
2. Every endpoint method in §4 has exactly one test in `EndpointSmokeTests` that asserts both the success status code AND one response-body invariant.
3. `coverage report -m --include='BTAPI/metrics.py'` still shows `100.0%` Cover with empty Missing.
4. No `.eml` files are written into `email/` during the test run (verified by `ls email/ | wc -l` before and after returning the same count).
5. `coverage report -m` shows `BTAPI/views.py` at noticeably higher coverage than today's 14.2% (informational only — exact number not graded).

## 11. Known issues left in place (logged for future cleanup)

These are pre-existing view-layer bugs that this sub-project deliberately works around rather than fixes. Each is sidestepped by the test fixture or test data choice as noted above.

1. **`.title()` username/PK lookup is fragile** — `get_full_report`, `get_assigned_defects`, `get_developer_metric`, `patch_update_report`, `post_comment` all apply `id.title()` to URL parameters, which silently mismatches if the underlying record is not TitleCase. Workaround: TitleCase all fixture identifiers.
2. **`get_assigned_defects` filters by stringified pk, not username** — `views.py:55` does `assignedToId=id.title()` where `assignedToId` is an FK to User. Behaves as a pk lookup. Workaround: pass `dev.pk` in the URL.
3. **Metric endpoint allows any authenticated user** — `views.py:71` uses `IsAuthenticated` only. Probably should be `IsOwner | IsDeveloper`. Sprint 3 doesn't specify.
4. **`patch_update_report` raw-string comparison at `views.py:101`** — `if new_status in ('Duplicate', 'Rejected')` checks the raw query param, but the case statement above already title-cased it. So passing `?status=duplicate` enters the branch but skips the notification path. Workaround: tests don't exercise this transition.

These belong to a future view-layer cleanup sub-project (not in Sprint 3 scope).

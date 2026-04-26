# API Documentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver Sprint 3 sub-project 4 — install and configure `drf-spectacular`, serve OpenAPI 3.0 docs from `/api/schema/`, `/api/schema/swagger-ui/`, `/api/schema/redoc/`, and decorate views so endpoints are grouped into 5 tags (Authentication, Defect Reports, Comments, Products, Metrics) each with a one-line summary.

**Architecture:** Add no new files. Mutate five existing files: `requirements.txt`, `BTConfig/settings.py`, `BTConfig/urls.py`, `BTAPI/views.py`, `BTAPI/urls.py`. Plus a README addition. The decoration depth matches what the COMP3297 lecture material covered (`SE_2026BC_05_3_DRF_2_Documentation.pdf`, pages 9–18) — tags + per-operation summaries, no per-parameter descriptions or response examples (those are Tier-C and out of scope).

**Tech Stack:** `drf-spectacular==0.29.0`, Django 6.0.3, Django REST Framework 3.17.1.

**Design spec:** `docs/superpowers/specs/2026-04-27-api-documentation-design.md`

---

## Pre-flight

- [ ] **Pre-flight Step 1: Confirm baseline state**

```bash
cd /Users/wangyamyuk13/Documents/GitHub/BetaTrax
source venv/bin/activate
python3 manage.py test --settings=BTConfig.settings_test BTAPI 2>&1 | grep -E '^Ran '
git status --short
```

Expected: `Ran 16 tests in 1.XXXs`. `git status --short` is empty (clean working tree from sub-project 3).

- [ ] **Pre-flight Step 2: Confirm Postgres is still reachable (we'll smoke-test schema endpoints against the real settings)**

```bash
export PATH="/Applications/Postgres.app/Contents/Versions/latest/bin:$PATH"
PGPASSWORD=password psql -h localhost -U admin -d btpostgres -c "SELECT 1" | head -3
```

Expected: a `1` row returned. If this fails, see `README.md` § Multi-tenancy Setup §3 to recreate the role and DB.

---

## Task 1: Install drf-spectacular and add to requirements

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Install in the active venv**

```bash
pip install drf-spectacular==0.29.0
python3 -c "import drf_spectacular; print(drf_spectacular.__version__)"
```

Expected: the second command prints `0.29.0`.

- [ ] **Step 2: Append to `requirements.txt`**

`requirements.txt` currently ends with:
```
sqlparse==0.5.5
coverage==7.6.10
```

Append one line:
```
drf-spectacular==0.29.0
```

The full file should now be:
```
asgiref==3.11.1
Django==6.0.3
django-tenants==3.10.1
djangorestframework==3.17.1
djangorestframework_simplejwt==5.5.1
psycopg2-binary==2.9.12
PyJWT==2.12.1
sqlparse==0.5.5
coverage==7.6.10
drf-spectacular==0.29.0
```

- [ ] **Step 3: Commit**

```bash
git commit --only requirements.txt -m "chore(deps): add drf-spectacular 0.29.0 for OpenAPI docs"
```

---

## Task 2: Configure drf-spectacular in settings.py

**Files:**
- Modify: `BTConfig/settings.py`

- [ ] **Step 1: Add `drf_spectacular` to `SHARED_APPS`**

In `BTConfig/settings.py`, the current `SHARED_APPS` reads:

```python
SHARED_APPS = [
    'django_tenants',
    'BTAPI',
    'rest_framework',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]
```

Add `'drf_spectacular',` immediately after `'rest_framework',`:

```python
SHARED_APPS = [
    'django_tenants',
    'BTAPI',
    'rest_framework',
    'drf_spectacular',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]
```

- [ ] **Step 2: Add `DEFAULT_SCHEMA_CLASS` to `REST_FRAMEWORK`**

Find the existing `REST_FRAMEWORK` block. It currently reads:

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    )
}
```

Replace it with (note the trailing comma after the renderer tuple, and the new `DEFAULT_SCHEMA_CLASS` key):

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}
```

- [ ] **Step 3: Add `SPECTACULAR_SETTINGS` block**

Append the following at the end of `settings.py` (after the existing `EMAIL_FILE_PATH = 'email'` line):

```python

SPECTACULAR_SETTINGS = {
    'TITLE': 'BetaTrax API',
    'DESCRIPTION': (
        'REST API for managing beta software defect reports. '
        'Multi-tenant SaaS deployment via django-tenants -- every '
        'request must hit a tenant subdomain (e.g. acme.localhost). '
        'Authentication is JWT via /api/token/.'
    ),
    'VERSION': '2.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'TAGS': [
        {'name': 'Authentication', 'description': 'JWT token obtain and refresh.'},
        {'name': 'Defect Reports', 'description': 'Submit, list, view, and update defect reports through the role-enforced status workflow.'},
        {'name': 'Comments', 'description': 'Comments threaded under defect reports.'},
        {'name': 'Products', 'description': 'Beta products under test.'},
        {'name': 'Metrics', 'description': 'Developer effectiveness classification per Sprint 3 §22-24.'},
    ],
}
```

- [ ] **Step 4: Verify Django still loads cleanly**

```bash
python3 manage.py check --settings=BTConfig.settings 2>&1 | tail -3
python3 manage.py check --settings=BTConfig.settings_test 2>&1 | tail -3
```

Expected: both print `System check identified no issues (0 silenced).` If either errors with `ModuleNotFoundError: No module named 'drf_spectacular'`, redo Task 1 Step 1.

- [ ] **Step 5: Commit**

```bash
git commit --only BTConfig/settings.py -m "feat(docs): wire drf-spectacular into settings

Adds drf_spectacular to SHARED_APPS, sets DEFAULT_SCHEMA_CLASS to
its AutoSchema, and provides SPECTACULAR_SETTINGS with the project
title, description, version, and the five tag definitions matching
the resource groupings used in the Postman collection."
```

---

## Task 3: Add the three schema URLs to project urls.py

**Files:**
- Modify: `BTConfig/urls.py`

- [ ] **Step 1: Replace the file contents**

`BTConfig/urls.py` currently reads:

```python
"""
URL configuration for BTConfig project.
... (boilerplate doc) ...
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('BTAPI.urls')),
]
```

Replace with:

```python
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('BTAPI.urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path(
        'api/schema/swagger-ui/',
        SpectacularSwaggerView.as_view(url_name='schema'),
        name='swagger-ui',
    ),
    path(
        'api/schema/redoc/',
        SpectacularRedocView.as_view(url_name='schema'),
        name='redoc',
    ),
]
```

(The boilerplate URL-config docstring is dropped — it's noise, and Sprint 3 §41 explicitly asks to "remove unnecessary clutter".)

- [ ] **Step 2: Smoke-test schema generation via the management command**

```bash
python3 manage.py spectacular --color --file /tmp/btschema.yml 2>&1 | tail -5
wc -l /tmp/btschema.yml
head -10 /tmp/btschema.yml
```

Expected: the command may print a few `WARN` lines about FBV inference (these are acceptable per spec §3); the yaml file is at least 100 lines; `head` shows `openapi: 3.0.3` and `info:` block with `title: BetaTrax API`. If `wc -l` shows < 50, schema generation broke — STOP and inspect the `WARN` output.

- [ ] **Step 3: Commit**

```bash
git commit --only BTConfig/urls.py -m "feat(docs): serve OpenAPI schema, Swagger UI, and ReDoc

Adds /api/schema/ (raw YAML), /api/schema/swagger-ui/ (interactive),
and /api/schema/redoc/ (read-only) routes per the COMP3297 lecture
pages 15-16.  Also drops the django-startproject docstring noise."
```

---

## Task 4: Decorate the 8 application views

**Files:**
- Modify: `BTAPI/views.py`

This task adds a `@extend_schema(...)` decorator to each of the 8 application view functions, plus the two new imports. The decorators go between `@permission_classes(...)` and `def view_name(...)`.

- [ ] **Step 1: Add the imports**

In `BTAPI/views.py`, the current imports block (lines 1–10) ends with:

```python
from .utils import *
from .metrics import classify_developer_effectiveness
```

Append two lines:

```python
from .utils import *
from .metrics import classify_developer_effectiveness
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
```

- [ ] **Step 2: Decorate `post_new_report`**

The current view (lines 12–23) reads:

```python
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def post_new_report(request): 
    serializer = DefectReportSerializer(data=request.data)
    ...
```

Insert one decorator between `@permission_classes(...)` and `def`:

```python
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@extend_schema(tags=['Defect Reports'], summary='Submit a new defect report')
def post_new_report(request): 
    serializer = DefectReportSerializer(data=request.data)
    ...
```

- [ ] **Step 3: Decorate `get_reports`**

Insert decorator:

```python
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@extend_schema(tags=['Defect Reports'], summary='List defect reports filtered by status')
def get_reports(request, status):
    ...
```

- [ ] **Step 4: Decorate `get_assigned_defects`**

```python
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsDeveloper | IsOwner])
@extend_schema(tags=['Defect Reports'], summary='List ASSIGNED reports for a developer')
def get_assigned_defects(request, id):
    ...
```

- [ ] **Step 5: Decorate `get_full_report`**

```python
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@extend_schema(tags=['Defect Reports'], summary='Get full detail of a defect report')
def get_full_report(request, id):
    ...
```

- [ ] **Step 6: Decorate `get_developer_metric`**

```python
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@extend_schema(tags=['Metrics'], summary='Get developer effectiveness classification')
def get_developer_metric(request, id):
    ...
```

- [ ] **Step 7: Decorate `patch_update_report` (with the 5 query-param declarations)**

This is the only endpoint that reads query string params inside the body, so we must declare them explicitly. Insert this multi-line decorator:

```python
@api_view(['PATCH'])
@permission_classes([IsAuthenticated, IsUser | IsOwner | IsDeveloper])
@extend_schema(
    tags=['Defect Reports'],
    summary='Update report status, severity, priority, or duplicate parent',
    parameters=[
        OpenApiParameter(
            name='status', type=OpenApiTypes.STR, required=False,
            location=OpenApiParameter.QUERY,
            description='New status (e.g. Open, Assigned, Fixed, Resolved, Reopened, Cannot Reproduce, Duplicate, Rejected). Role-enforced.',
        ),
        OpenApiParameter(
            name='severity', type=OpenApiTypes.STR, required=False,
            location=OpenApiParameter.QUERY,
            description='New severity (Low, Minor, Major, Critical).',
        ),
        OpenApiParameter(
            name='priority', type=OpenApiTypes.STR, required=False,
            location=OpenApiParameter.QUERY,
            description='New priority (Low, Medium, High, Critical).',
        ),
        OpenApiParameter(
            name='parent', type=OpenApiTypes.STR, required=False,
            location=OpenApiParameter.QUERY,
            description='Defect ID of the parent report (used when marking this report as a duplicate).',
        ),
        OpenApiParameter(
            name='dev', type=OpenApiTypes.STR, required=False,
            location=OpenApiParameter.QUERY,
            description='User ID of the developer to (re)assign this report to.',
        ),
    ],
)
def patch_update_report(request, id):  
    ...
```

- [ ] **Step 8: Decorate `post_comment`**

```python
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@extend_schema(tags=['Comments'], summary='Post a comment on a defect report')
def post_comment(request, id): 
    ...
```

- [ ] **Step 9: Decorate `post_new_product`**

```python
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsOwner | IsDeveloper])
@extend_schema(tags=['Products'], summary='Register a new product')
def post_new_product(request):
    ...
```

- [ ] **Step 10: Verify Django still loads + tests still pass + schema regenerates**

```bash
python3 manage.py check --settings=BTConfig.settings 2>&1 | tail -3
python3 manage.py test --settings=BTConfig.settings_test BTAPI 2>&1 | grep -E '^Ran '
python3 manage.py spectacular --color --file /tmp/btschema.yml 2>&1 | tail -3
grep -c 'tags:' /tmp/btschema.yml
grep -c 'summary:' /tmp/btschema.yml
```

Expected: check passes; `Ran 16 tests`; spectacular runs (warnings still acceptable); `tags:` count is 9 (the 5 declarations in TAGS plus one per documented operation; numbers approximate); `summary:` count is at least 8 (one per decorated app view, plus simplejwt's defaults).

- [ ] **Step 11: Commit**

```bash
git commit --only BTAPI/views.py -m "feat(docs): tag and summarise the 8 application endpoints

@extend_schema decorators add tags + per-operation summaries to every
application view, matching the lecture's pages 17-18 polish steps.
patch_update_report also gets explicit OpenApiParameter entries for
its 5 query-string parameters that drf-spectacular cannot infer
from the @api_view function signature."
```

---

## Task 5: Tag the simplejwt token views as Authentication

**Files:**
- Modify: `BTAPI/urls.py`

The `TokenObtainPairView` and `TokenRefreshView` come from the `simplejwt` package — we can't add `@extend_schema` to their source, but we can wrap their `as_view()` results at URL-config time.

- [ ] **Step 1: Replace the contents of `BTAPI/urls.py`**

The current file reads:

```python
from django.urls import path
from .views import *
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('defect/', post_new_report, name='post_new_report'),
    path('reports/<str:status>/', get_reports, name='get_reports'),
    path('reports/assigned/<str:id>/', get_assigned_defects, name='get_assigned_defects'),
    path('defect/<str:id>/', get_full_report, name='get_full_report'),
    path('update/<str:id>/', patch_update_report, name='patch_update_report'),
    path('comment/<str:id>/', post_comment, name='post_comment'),
    path('product/', post_new_product, name='post_new_product'),
    path('metric/<str:id>/', get_developer_metric, name='get_developer_metric'),
]
```

Replace with:

```python
from django.urls import path
from drf_spectacular.utils import extend_schema
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from .views import *

token_obtain_view = extend_schema(
    tags=['Authentication'],
    summary='Obtain a JWT access + refresh token pair',
)(TokenObtainPairView.as_view())

token_refresh_view = extend_schema(
    tags=['Authentication'],
    summary='Exchange a refresh token for a new access token',
)(TokenRefreshView.as_view())

urlpatterns = [
    path('token/', token_obtain_view, name='token_obtain_pair'),
    path('token/refresh/', token_refresh_view, name='token_refresh'),
    path('defect/', post_new_report, name='post_new_report'),
    path('reports/<str:status>/', get_reports, name='get_reports'),
    path('reports/assigned/<str:id>/', get_assigned_defects, name='get_assigned_defects'),
    path('defect/<str:id>/', get_full_report, name='get_full_report'),
    path('update/<str:id>/', patch_update_report, name='patch_update_report'),
    path('comment/<str:id>/', post_comment, name='post_comment'),
    path('product/', post_new_product, name='post_new_product'),
    path('metric/<str:id>/', get_developer_metric, name='get_developer_metric'),
]
```

The route paths and URL names are unchanged — only the view callables for the two token paths are wrapped.

- [ ] **Step 2: Verify the JWT flow still works (the 2 token tests in `EndpointSmokeTests` cover this)**

```bash
python3 manage.py test --settings=BTConfig.settings_test \
    BTAPI.tests.EndpointSmokeTests.test_post_token_returns_access_and_refresh \
    BTAPI.tests.EndpointSmokeTests.test_post_token_refresh_returns_new_access \
    -v 2 2>&1 | tail -10
```

Expected: `Ran 2 tests in 0.0XXs · OK`. Both token tests still pass — the `extend_schema` wrapper is transparent to the JWT auth flow.

- [ ] **Step 3: Verify the schema now includes the Authentication tag on token endpoints**

```bash
python3 manage.py spectacular --color --file /tmp/btschema.yml 2>&1 | tail -3
grep -A2 '/api/token/:' /tmp/btschema.yml | head -10
```

Expected: the token endpoint's spec block contains `- Authentication` under `tags:` and the summary string.

- [ ] **Step 4: Commit**

```bash
git commit --only BTAPI/urls.py -m "feat(docs): tag simplejwt token endpoints under Authentication

Wraps TokenObtainPairView and TokenRefreshView with extend_schema at
URL-config time so the docs group them under the Authentication tag
with friendly summaries.  The simplejwt source is not modified;
URL names and route paths are unchanged."
```

---

## Task 6: Add the API Documentation section to README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Locate insertion point**

```bash
grep -n '^## ' README.md
```

The new section goes between the existing `## Multi-tenancy Setup ...` block and `## Testing & Coverage`.

- [ ] **Step 2: Insert the section**

Find the line `## Testing & Coverage` and insert this block immediately *before* it:

````markdown
## API Documentation

The full BetaTrax API is documented via [`drf-spectacular`](https://drf-spectacular.readthedocs.io/) as an OpenAPI 3.0 specification.

After starting the dev server (`python3 manage.py runserver`), visit:

| URL | Purpose |
|---|---|
| `http://localhost:8000/api/schema/` | Raw OpenAPI 3.0 YAML schema |
| `http://localhost:8000/api/schema/swagger-ui/` | Interactive Swagger UI (try endpoints in-browser) |
| `http://localhost:8000/api/schema/redoc/` | ReDoc (read-only, easier-to-print layout) |

To export the schema as a file:

```bash
python3 manage.py spectacular --color --file schema.yml
```

A complementary [Postman collection](postman/collections/) lives under `postman/` with example requests for each endpoint.

> ⚠️ The schema is tenant-agnostic. When testing endpoints, substitute the tenant subdomain — e.g. `acme.localhost:8000` instead of `localhost:8000`.

````

- [ ] **Step 3: Commit**

```bash
git commit --only README.md -m "docs(readme): add API Documentation section

Documents the three drf-spectacular URLs (schema, swagger-ui, redoc),
the manage.py spectacular export command, and the Postman complement."
```

---

## Task 7: Final verification

- [ ] **Step 1: Confirm no regressions in the test suite**

```bash
python3 manage.py test --settings=BTConfig.settings_test BTAPI 2>&1 | grep -E '(Ran|OK|FAIL|ERROR)'
```

Expected: `Ran 16 tests in 1.XXXs` and `OK`.

- [ ] **Step 2: Confirm classifier coverage still 100%**

```bash
coverage run --rcfile=.coveragerc manage.py test --settings=BTConfig.settings_test BTAPI 2>&1 | tail -3
coverage report -m --include='BTAPI/metrics.py'
```

Expected: tests pass; `BTAPI/metrics.py` shows `100.0%` Cover, empty Missing.

- [ ] **Step 3: Confirm schema generation is clean**

```bash
python3 manage.py spectacular --color --file /tmp/btschema.yml 2>&1 | tail -10
echo "---"
wc -l /tmp/btschema.yml
echo "---"
grep -E '^  /api/' /tmp/btschema.yml
```

Expected: schema generates with at most warnings (no errors); >100 lines; the path list contains `/api/token/`, `/api/token/refresh/`, `/api/defect/`, `/api/reports/{status}/`, `/api/reports/assigned/{id}/`, `/api/defect/{id}/`, `/api/update/{id}/`, `/api/comment/{id}/`, `/api/product/`, `/api/metric/{id}/`.

- [ ] **Step 4: Confirm all 5 tag groups appear in the schema**

```bash
grep -B1 'description:' /tmp/btschema.yml | grep -E 'Authentication|Defect Reports|Comments|Products|Metrics' | head -15
```

Expected: at least one match per tag name.

- [ ] **Step 5: Confirm the live UI works (manual browser check)**

Start the dev server and visit each URL in a browser:

```bash
python3 manage.py runserver 127.0.0.1:8000
```

Then in a browser:
- `http://localhost:8000/api/schema/swagger-ui/` — should render the Swagger UI with 5 collapsible tag groups.
- `http://localhost:8000/api/schema/redoc/` — should render ReDoc with the same content.
- `http://acme.localhost:8000/api/schema/swagger-ui/` — should render identically (the schema is tenant-agnostic).

Stop the server when done (`Ctrl-C` if foreground; `pkill -f 'manage.py runserver'` if background).

- [ ] **Step 6: Confirm git history**

```bash
git log --oneline -10
```

Expected (most recent first):

```
docs(readme): add API Documentation section
feat(docs): tag simplejwt token endpoints under Authentication
feat(docs): tag and summarise the 8 application endpoints
feat(docs): serve OpenAPI schema, Swagger UI, and ReDoc
feat(docs): wire drf-spectacular into settings
chore(deps): add drf-spectacular 0.29.0 for OpenAPI docs
docs: add Sprint 3 sub-project 4 design (API documentation)
... (sub-project 3 commits)
```

- [ ] **Step 7: Confirm working tree is clean**

```bash
git status --short
```

Expected: empty output.

---

## Acceptance criteria (from spec §9)

1. ✅ `manage.py spectacular --color --file /tmp/schema.yml` exits 0 and writes >100 lines → Task 7 Step 3.
2. ✅ `curl http://acme.localhost:8000/api/schema/` returns YAML containing `BetaTrax API`, `Defect Reports`, `Authentication`, `Metrics` → Task 7 Step 4 (via grep on the file generated in Step 3).
3. ✅ Swagger UI shows 5 tag groups with summaries and an Authorize button → Task 7 Step 5 (manual browser check).
4. ✅ ReDoc shows the same content → Task 7 Step 5.
5. ✅ `patch_update_report` shows 5 query parameters with descriptions → verified by viewing the endpoint in Swagger UI in Task 7 Step 5.
6. ✅ README documents both UI URLs and the export command → Task 6.
7. ✅ All 16 tests still pass → Task 7 Step 1.
8. ✅ Classifier coverage still 100% → Task 7 Step 2.

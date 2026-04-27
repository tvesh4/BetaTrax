# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BetaTrax is a Django REST API for managing beta software defect reports (COMP3297 Group F project). Testers submit defect reports; product owners and developers manage them through a role-enforced status workflow. As of Sprint 3 the deployment is multi-tenant via `django-tenants` on PostgreSQL — every request must hit a tenant subdomain (e.g. `acme.localhost:8000`).

## Setup & Commands

```bash
# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Database setup (PostgreSQL via django-tenants — see README.md "Multi-tenancy Setup")
python3 manage.py migrate_schemas --shared    # public schema (admin, auth, tenant metadata)
python3 manage.py migrate_schemas             # tenant schemas
python3 manage.py bootstrap_tenants           # creates public + acme.localhost + globex.localhost demo tenants

# Create admin user (public schema)
python3 manage.py createsuperuser

# Run development server
python3 manage.py runserver

# Run tests (SQLite-backed, strips django-tenants for speed)
python3 manage.py test --settings=BTConfig.settings_test BTAPI

# Run a single test
python3 manage.py test --settings=BTConfig.settings_test BTAPI.tests.ClassifierTests.test_at_threshold_zero_reopened_returns_good

# Coverage (Sprint 3 §25 — full statement + branch on BTAPI/metrics.py)
coverage run --rcfile=.coveragerc manage.py test --settings=BTConfig.settings_test BTAPI
coverage report -m --include='BTAPI/metrics.py'
```

## Architecture

**Two Django apps:**
- `BTConfig/` — Django project config (`settings.py` for prod/dev Postgres+tenants, `settings_test.py` for SQLite test runs, root URLs, ASGI/WSGI)
- `BTAPI/` — All models, serializers, views, permissions, utils, metrics, tenant bootstrap command, and URL routes

**Request flow:** `TenantMainMiddleware` resolves the request's hostname to a tenant schema → `BTConfig/urls.py` → `/api/` prefix → `BTAPI/urls.py` → `@api_view` functions in `views.py`. All ORM queries on tenant tables are automatically scoped to the active schema by `TenantSyncRouter`.

**Multi-tenancy (`django-tenants`):**
- `BTAPI.Client` is the tenant model (`TENANT_MODEL`) with `auto_create_schema=True`; `BTAPI.Domain` maps hostnames to tenants (`TENANT_DOMAIN_MODEL`).
- `SHARED_APPS` (public schema only): `django_tenants`, admin, auth, sessions, drf, drf_spectacular.
- `TENANT_APPS` (per-tenant schema): `BTAPI`, auth, drf. `BTAPI` is dual-listed in both — see "Known limitations" below.
- `*.localhost` resolves to `127.0.0.1` automatically on macOS, no `/etc/hosts` edit required.
- `bootstrap_tenants` management command idempotently creates the `public`, `acme`, and `globex` tenants with sample users/products/defects per tenant (passwords `pw`).

**Authentication:** JWT via `simplejwt`. Tokens are obtained at `POST /api/token/` and include custom claims: `username`, `is_owner`, `is_developer` (see `UserTokenObtainPairSerializer`). All endpoints (except `/api/token/`, `/api/token/refresh/`, and the `/api/schema/*` doc routes) require `IsAuthenticated`. JWTs are tenant-scoped — a token issued by `acme.localhost` is meaningless against `globex.localhost`.

**Authorization:** `BTAPI/permissions.py` defines three permission classes — `IsUser`, `IsDeveloper`, `IsOwner` — which check Django group membership (`User`, `Developer`, `Owner`). Groups are loaded from `groups.json`; users are assigned to groups via Django Admin. `bootstrap_tenants` creates the three groups inside each tenant schema.

**API Endpoints (mounted under `/api/`):**
- `POST /api/token/` — Login, returns JWT access + refresh tokens
- `POST /api/token/refresh/` — Refresh access token
- `POST /api/defect/` — Submit new defect report (`IsAuthenticated`)
- `GET /api/reports/<status>/` — List reports by status; supports `NEW`, `OPEN`, `ASSIGNED`, `FIXED`, `RESOLVED`, `REOPENED`, `CLOSED`, `ALL`
- `GET /api/reports/assigned/<id>/` — List ASSIGNED reports for a developer (`IsDeveloper | IsOwner`)
- `GET /api/defect/<id>/` — Full report details
- `PATCH /api/update/<id>/` — Update report status, severity, priority, parent (duplicate link), or reassign developer; role-enforced transitions. Mutations come from query params (`?status=...&severity=...&priority=...&parent=...&dev=...`).
- `POST /api/comment/<id>/` — Post a comment on a report
- `POST /api/product/` — Register a new product (`IsOwner | IsDeveloper`)
- `GET /api/metric/<id>/` — Developer effectiveness classification (`IsAuthenticated`); `<id>` is the developer's username
- `GET /api/schema/` — Raw OpenAPI 3.0 YAML (drf-spectacular)
- `GET /api/schema/swagger-ui/` — Swagger UI
- `GET /api/schema/redoc/` — ReDoc

**Defect status workflow (role-enforced in `patch_update_report`):**
```
NEW → OPEN | DUPLICATE | REJECTED                 (Owner)
OPEN | REOPENED → ASSIGNED                        (Developer; sets assignedToId = self)
ASSIGNED → FIXED | CANNOT REPRODUCE               (Developer; FIXED bumps developer.fixedCount)
FIXED → RESOLVED | REOPENED                       (Owner; REOPENED bumps developer.reopenedCount)
```
The terminal "closed" states are now three distinct values — `Cannot Reproduce`, `Duplicate`, `Rejected` — not a single `CLOSED`. Setting `parent` on a NEW report and moving it to `Duplicate`/`Rejected` triggers duplicate-link emails to both testers.

**Key model relationships:**
- `Client` / `Domain` — django-tenants tenant + hostname mapping (public schema only)
- `Developer` — OneToOne to `auth.User` (related_name `developer_profile`); tracks `fixedCount` and `reopenedCount` used by the effectiveness classifier
- `Product` — FKs to `auth.User` for `ownerId` and `devId`; no separate Tester model (testers are users in the `User` group)
- `DefectReport` — FKs to `Product`, `auth.User` for `testerId` and `assignedToId`, and a self-referential FK `parent` for duplicate linking (with `children` reverse relation). Has a `clean()` guard preventing self-parenting; deeper cycles (A→B→A) are not enforced.
- `Comment` — FK to `DefectReport` (CASCADE), ordered by `-createdAt`

**Email notifications:** `BTAPI/utils.py` provides four functions called from `views.py`:
- `send_status_update_email(report)` — notifies tester on any status change
- `send_po_update_email(report)` — notifies product owner on status change
- `send_duplicate_update_email(report, dup_report)` — notifies tester when report is linked as duplicate
- `send_children_update_email(report)` — notifies testers of child reports when parent is updated

Emails are written to the `email/` directory (file-based backend in `BTConfig/settings.py`); the test settings module switches this to `locmem` so tests don't litter the filesystem.

**Serializers (`BTAPI/serializer.py`):**
- `DefectReportSerializer` — full report with nested `comments` and `children` (read-only), writable `parent`
- `ReportLiteSerializer` — `id`, `title`, `status` only; used by list endpoints
- `ProductSerializer` — exposes `ownerId` as `ownerId.username` (read-only)
- `CommentSerializer` — exposes `authorId` as `authorUsername` (read-only)
- `UserTokenObtainPairSerializer` — extends simplejwt, adds `username`/`is_owner`/`is_developer` claims

**Developer effectiveness metric (`BTAPI/metrics.py`):**
- `classify_developer_effectiveness(fixed_count, reopened_count) -> str`
  - `fixed_count < 20` → `"Insufficient data"`
  - ratio `< 1/32` → `"Good"`
  - ratio `< 1/8` → `"Fair"`
  - else → `"Poor"`
- Pure function, no DB; six tests in `BTAPI/tests.py::ClassifierTests` give 100% statement + branch coverage. `.coveragerc` enforces `branch = True` and pins the source/omit set used by the §25 grading hook.

**API documentation:** `drf-spectacular` generates the OpenAPI 3.0 schema from `@extend_schema` decorators in `BTAPI/views.py` and an `extend_schema_view` wrapper in `BTAPI/urls.py` for the simplejwt token views. Tag groups (`Authentication`, `Defect Reports`, `Comments`, `Products`, `Metrics`) are configured in `SPECTACULAR_SETTINGS`. `@extend_schema` must be the OUTERMOST decorator (above `@api_view`) on FBVs — placing it between `@api_view` and `@permission_classes` produces empty tags/summaries.

## Test Settings (`BTConfig/settings_test.py`)

Fast local test runs use a SQLite-backed test settings module that strips the tenants layer:

```python
from .settings import *
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
DATABASE_ROUTERS = ()
INSTALLED_APPS = [a for a in INSTALLED_APPS if a != 'django_tenants']
MIDDLEWARE = [m for m in MIDDLEWARE if 'django_tenants' not in m]
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
```

Tests under `settings_test` do **not** exercise tenant isolation — a second pass under the real Postgres + tenants config is required for full validation of multi-tenant behavior.

## Known Limitations

- `BTAPI` is dual-listed in `SHARED_APPS` and `TENANT_APPS`, so per-tenant data tables (`Developer`, `Product`, `DefectReport`, `Comment`) get created in *both* the public schema and every tenant schema. Isolation still works correctly via the router; the public-schema copies are unused shadow tables. Cleanup would split `BTAPI` into a `BTTenants` app for `Client`/`Domain` plus a tenant-only `BTAPI`.
- `views.py` has a few latent bugs that are sidestepped (not fixed) by the test fixture conventions: `.title()` on URL params (case-fragile lookups), `assignedToId=id.title()` filtering an FK column with a string, and `new_status in ('Duplicate', 'Rejected')` after `new_status` was reassigned to `new_status.title()` above. Test IDs are TitleCase to keep the suite green; fixing these is out of scope.
- Circular duplicates: A → A is blocked by `DefectReport.clean()`, but deeper cycles (A → B → A) are not enforced.
- The 50+ migration history from the SQLite era was not squashed.

## Key Constraints

- User/Developer/Owner accounts are created by a superuser via Django Admin (per tenant); self-registration is not supported.
- BrowsableAPIRenderer is disabled; API returns JSON only.
- Production database is PostgreSQL with `django-tenants`. SQLite (`db.sqlite3`) is only used by the in-memory test database and is gitignored.
- Django migrations under `BTAPI/migrations/` ARE tracked in git.
- The `email/` and `htmlcov/` directories and the `.coverage` file are gitignored.

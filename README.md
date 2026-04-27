# BetaTrax
Group F of COMP3297 2025-2026 Semester 2

## Setup & Installation
1. Create and activate virtual environment:
   `python3 -m venv venv`
   `source venv/bin/activate`
2. Install dependencies: `pip install -r requirements.txt`
3. Apply migrations: `python3 manage.py migrate`
4. Load user groups `python3 manage.py loaddata groups.json`
5. Start the development server: `python3 manage.py runserver`

> ⚠️ **Sprint 3 note:** the steps above are the legacy single-tenant path (SQLite). For Sprint 3, BetaTrax runs on PostgreSQL with `django-tenants`. The active `BTConfig/settings.py` targets Postgres, so `manage.py migrate` is replaced by `manage.py migrate_schemas`. See **Multi-tenancy Setup** below for the full workflow.

## Multi-tenancy Setup (PostgreSQL + django-tenants)

BetaTrax is configured for the *single-database, separate-schema* multi-tenancy pattern via [`django-tenants`](https://django-tenants.readthedocs.io/). Each customer (a development company) gets its own PostgreSQL schema; the API routes requests to the right schema based on the request's hostname.

### 1. Install PostgreSQL

Either:
- **Postgres.app** — download from [postgresapp.com](https://postgresapp.com/) and launch. Server runs on `localhost:5432` by default.
- **Homebrew** — `brew install postgresql@16 && brew services start postgresql@16`.

### 2. Make the Postgres CLI tools available

For Postgres.app:

```bash
# Current shell only:
export PATH="/Applications/Postgres.app/Contents/Versions/latest/bin:$PATH"

# Persistent (zsh):
echo 'export PATH="/Applications/Postgres.app/Contents/Versions/latest/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### 3. Create the role and database

```bash
createuser --superuser admin
psql -d postgres -c "ALTER USER admin WITH PASSWORD 'password';"
createdb -O admin btpostgres
```

The credentials match `BTConfig/settings.py`. The `--superuser` flag is required because `django-tenants` issues `CREATE SCHEMA` at runtime when `auto_create_schema=True` Clients are saved.

Verify connectivity:

```bash
PGPASSWORD=password psql -h localhost -U admin -d btpostgres -c '\conninfo'
```

### 4. Apply migrations

`django-tenants` replaces Django's `migrate` with `migrate_schemas`:

```bash
python3 manage.py migrate_schemas --shared    # public schema (admin, auth, tenant metadata)
python3 manage.py migrate_schemas             # tenant schemas (none yet, no-op first time)
```

### 5. Bootstrap demo tenants

```bash
python3 manage.py bootstrap_tenants
```

This idempotently creates the public tenant plus the two demo tenants prescribed by the Final Review setup spec (all sample-user passwords are `pw`):

- The **public** tenant (admin/management, no API data).
- **SE Tenant 1** (`se1.localhost`) — users `user_1`–`user_5` plus `Tester_1` (email `icyreward@gmail.com`), product `prod_1` (PO=`user_1`, dev=`user_2`), one Assigned defect `Dr1` titled "Unable to search" (Severity Major / Priority High, submitted 2026-03-25 10:53, assigned to `user_2`).
- **SE Tenant 2** (`se2.localhost`) — users `user_6`–`user_8` plus `Tester_1`, product `prod_1` (same primary key, different schema; PO=`user_6`, dev=`user_7`), one Assigned defect `Dr1` titled "Hit count incorrect" (Severity Minor / Priority High, submitted 2026-04-27 15:37, assigned to `user_7`) with two comments dated 2026-04-26. `user_7` is seeded with `fixedCount=8`, `reopenedCount=1` for the developer-effectiveness demo. `user_8` is in the `Developer` group but is not the FK-linked dev of `prod_1` (model limitation, see below).

The command also drops obsolete `acme`/`globex` schemas if present, so it's safe to re-run on a database created by the previous bootstrap.

### 6. Create a superuser for the public admin

```bash
python3 manage.py createsuperuser
```

Then visit `http://localhost:8000/admin/` to manage tenants and domains.

### 7. Verify the demo works

Start the dev server:

```bash
python3 manage.py runserver
```

In another terminal:

```bash
# 1. Acquire a token in SE Tenant 1 — must succeed
curl -X POST http://se1.localhost:8000/api/token/ \
    -H "Content-Type: application/json" \
    -d '{"username":"user_1","password":"pw"}'

# 2. Same user, SE Tenant 2 — must fail with 401 (user does not exist there)
curl -X POST http://se2.localhost:8000/api/token/ \
    -H "Content-Type: application/json" \
    -d '{"username":"user_1","password":"pw"}'

# 3. Per-tenant data isolation — each list contains only its own defect Dr1
curl -H "Authorization: Bearer <SE1_ACCESS_TOKEN>" \
    http://se1.localhost:8000/api/reports/ALL/
curl -H "Authorization: Bearer <SE2_ACCESS_TOKEN>" \
    http://se2.localhost:8000/api/reports/ALL/
```

`*.localhost` resolves to `127.0.0.1` automatically on macOS — no `/etc/hosts` edit is required.

### Limitations

1. The `BTAPI` app is dual-listed in `SHARED_APPS` and `TENANT_APPS`. Effect: per-tenant data tables (`Developer`, `Product`, `DefectReport`, `Comment`) get created in *both* the public schema and every tenant schema. Per-tenant isolation still works correctly because `TenantSyncRouter` directs reads/writes to the active schema, but the public-schema copies are unused shadow tables. A future cleanup would split `BTAPI` into a `BTTenants` app for `Client`/`Domain` plus a tenant-only `BTAPI`.
2. The automated test suite (`BTConfig.settings_test`) strips `django_tenants` and runs on in-memory SQLite, so it does not exercise tenant isolation. A second test pass under the real Postgres + tenants config is required for full validation.
3. The migration history (50 BTAPI migrations from the SQLite era) was not squashed. Some migrations are likely redundant. Cleanup is out of scope for Sprint 3.

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

> ⚠️ The schema is tenant-agnostic. When testing endpoints, substitute the tenant subdomain — e.g. `se1.localhost:8000` instead of `localhost:8000`.

## Testing & Coverage

The active settings module (`BTConfig/settings`) targets PostgreSQL with `django-tenants`. For fast local test runs without standing up Postgres, this project ships a SQLite-backed test-only settings module (`BTConfig.settings_test`) that strips the tenants layer.

> ⚠️ Tests under `settings_test` do **not** exercise tenant isolation. A second pass under the real Postgres + tenants configuration is required once Sub-project 3 (multi-tenancy) lands.

### Run the test suite

```bash
python3 manage.py test --settings=BTConfig.settings_test BTAPI
```

### Measure statement and branch coverage

The Sprint 3 §25 rubric requires full statement and full branch coverage of the developer-effectiveness classifier (`BTAPI/metrics.py`).

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

Step 3 must show `100.0%` under `Cover` for `BTAPI/metrics.py` with an empty `Missing` column. The six cases in `BTAPI/tests.py::ClassifierTests` are what produce that result.

## Key Assumptions for Sprint 1 Executable
- This increment is configured for 1 product. A default product (e.g., with ID "PROD-1") must be created via the Django Admin interface before use. All submitted defect reports are associated with this product.
- Authentication for Product Owners and Developers is out of scope for this sprint. API endpoints assume the requests are from an authenticated source. User records for Product Owners and Developers must be created via the Django Admin interface to allow assignment.
- Django is configured to write emails to the console for easy testing as per technical note. Actually emails are not sent.

## Key Assumptions for Sprint 2 Increment
- **Multi-Product Support:** Unlike Sprint 1, the system now supports multiple products. Product Owners (POs) can register new products directly via the API.
- **Role-Based Workflow:** While user registration remains an Admin-only task, the API now enforces status transitions based on roles (e.g., only Developers can mark a bug as "Fixed"; only Testers can "Reopen").
- **Duplicate Logic:** Marking a report as a duplicate via the `parent_report` field automatically triggers a terminal "Closed" state to prevent redundant work.
- **Email Simulation:** Emails are still configured to output to the console/logs to verify PBI-1 and PBI-4 notification requirements without external SMTP setup.

## Key Assumptions for Sprint 3 Increment
- **Multi-Tenancy Support:** Each customer (a software development company) gets its own PostgreSQL schema via `django-tenants`. Tenant routing is hostname-based (`se1.localhost`, `se2.localhost`). JWT tokens are tenant-scoped — a token issued by one tenant is meaningless against another. Tenants are bootstrapped through the `bootstrap_tenants` management command; live onboarding is supported via `Client.objects.create(...)` plus a `Domain.objects.create(...)` row (the underlying schema is created automatically because `Client.auto_create_schema = True`).
- **Developer Metrics:** A new pure function `BTAPI.metrics.classify_developer_effectiveness(fixed, reopened)` returns one of `Insufficient data` (fixed < 20), `Good` (ratio < 1/32), `Fair` (ratio < 1/8), or `Poor` (otherwise). Exposed at `GET /api/metric/<username>/`. The classifier is intentionally conservative on small samples — fewer than 20 fixed defects yields `Insufficient data` rather than a noisy verdict.
- **Automated Testing:** Sixteen tests under `BTAPI/tests.py` — ten happy-path endpoint smokes (one per endpoint method, satisfying §38) plus six classifier unit tests that produce 100% statement and branch coverage on `BTAPI/metrics.py` (the §25 grading hook). Tests run under `BTConfig.settings_test`, a SQLite-backed module that strips `django_tenants` for speed; tenant isolation is therefore not exercised by the suite (see Limitations).

## Limitations / Functionality Not Working Correctly
- **Self-Service Registration:** New Product Owners and Developers must still be created by a Superuser via `/admin` before they can be assigned to products or reports.
- **Single Developer per Product:** `Product.devId` is a single FK to `auth.User`. The Final Review setup spec lists two developers (`user_7` and `user_8`) for SE Tenant 2's product; the bootstrap therefore links `user_7` only and seeds `user_8` as a `Developer` in the tenant without an FK to the product. Promoting `devId` to `ManyToManyField` is queued for Sprint 4.
- **Tenant-Aware Test Pass Pending:** The automated suite runs on SQLite without `django_tenants`; multi-tenant isolation was validated via the manual smoke test in `docs/sprint-3-demo-runbook.md` §1. A Postgres-backed test pass remains on the Sprint 4 backlog.
- **Latent `.title()` Lookups in `views.py`:** Most URL-id lookups still call `.title()` (defect/comment/update endpoints), so seeded IDs are TitleCase (`Dr1`, `Cmt1`, `Cmt2`) to remain stable. The metric endpoint was fixed in Sprint 3 so spec-compliant lowercase usernames resolve.

## API Endpoints Implemented

Application endpoints:
- `POST /api/defect/` — Submit a new defect report. (PBI-1)
- `GET  /api/reports/<str:status>/` — List reports filtered by status (`NEW`, `OPEN`, `ASSIGNED`, `FIXED`, `RESOLVED`, `REOPENED`, `CLOSED`, `ALL`). (PBI-10)
- `GET  /api/reports/assigned/<str:id>/` — View all `ASSIGNED` reports for a specific developer. (PBI-3)
- `GET  /api/defect/<str:id>/` — View full detail of a specific defect report.
- `PATCH /api/update/<str:id>/` — Update report status, severity, priority, parent duplicate link, or reassign a developer. (PBI-6, 7, 8, 9)
- `POST /api/comment/<str:id>/` — Post a new comment on a defect report. (PBI-6 in Sprint 1)
- `POST /api/product/` — Register a new product. (PBI-5)
- `GET  /api/metric/<str:id>/` — Get developer-effectiveness classification (Sprint 3 §22-24). `<id>` is the developer's username.

Authentication endpoints (simplejwt):
- `POST /api/token/` — Obtain a JWT access + refresh token pair.
- `POST /api/token/refresh/` — Exchange a refresh token for a new access token.

API documentation endpoints (drf-spectacular):
- `GET /api/schema/` — Raw OpenAPI 3.0 YAML schema.
- `GET /api/schema/swagger-ui/` — Interactive Swagger UI.
- `GET /api/schema/redoc/` — ReDoc (read-only, easier-to-print layout).

## Sprint 3 Contributions

- **Lam Chin Yui:** *Product Backlog, Use Cases*
- **Lai Tsz Ng:** *Source Code*
- **Wang Yam Yuk:** *Source Code*
- **Kumar Tvesha Sanjay:** *API Documentation*

## Team Members & Contributions (Sprint 1 + Sprint 2)
- **Lam Chin Yui:** Product Backlog, Partial Domain Model
- **Lai Tsz Ng:** Communications, UI Storyboards, Source Code
- **Wang Yam Yuk:** UI Storyboards, Source Code
- **Kumar Tvesha Sanjay:** Product Backlog, Partial Domain Model

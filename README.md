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

This idempotently creates:
- The **public** tenant (admin/management, no API data).
- The **ACME Corp** tenant (`acme.localhost`) with users `AcmePo`, `AcmeDev`, `AcmeTester` (password `pw`), one product `AcmeProd1`, one defect `AcmeDef1`.
- The **Globex** tenant (`globex.localhost`) with users `GlobexPo`, `GlobexDev`, `GlobexTester` (password `pw`), one product `GlobexProd1`, one defect `GlobexDef1`.

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
# 1. Acquire a token in ACME — must succeed
curl -X POST http://acme.localhost:8000/api/token/ \
    -H "Content-Type: application/json" \
    -d '{"username":"AcmePo","password":"pw"}'

# 2. Same user, Globex tenant — must fail with 401 (user does not exist there)
curl -X POST http://globex.localhost:8000/api/token/ \
    -H "Content-Type: application/json" \
    -d '{"username":"AcmePo","password":"pw"}'

# 3. Per-tenant data isolation — each list contains only its own defect
curl -H "Authorization: Bearer <ACME_ACCESS_TOKEN>" \
    http://acme.localhost:8000/api/reports/ALL/
curl -H "Authorization: Bearer <GLOBEX_ACCESS_TOKEN>" \
    http://globex.localhost:8000/api/reports/ALL/
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

> ⚠️ The schema is tenant-agnostic. When testing endpoints, substitute the tenant subdomain — e.g. `acme.localhost:8000` instead of `localhost:8000`.

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
- **Multi-Tenancy Support:**
- **Developer Metrics**
- **Automated Testing**

## Limitations / Functionality Not Working Correctly
- **Self-Service Registration:** New Product Owners and Developers must still be created by a Superuser via `/admin` before they can be assigned to products or reports.

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

> **TEAM: please replace the bullets below with each member's actual Sprint 3 contributions before submission.**

- **Lam Chin Yui:** *[TODO: Sprint 3 contributions]*
- **Lai Tsz Ng:** *[TODO: Sprint 3 contributions]*
- **Wang Yam Yuk:** Multi-tenancy implementation (django-tenants + PostgreSQL, `Client`/`Domain` models, `bootstrap_tenants` management command); developer-effectiveness classifier (`BTAPI/metrics.py`) with full statement + branch coverage; automated endpoint tests (`EndpointSmokeTests`, `ClassifierTests`); SQLite-backed test settings module; API documentation via drf-spectacular (Swagger UI + ReDoc + exported `schema.yml`); README, CLAUDE, and demo-runbook updates.
- **Kumar Tvesha Sanjay:** *[TODO: Sprint 3 contributions]*

## Team Members & Contributions (Sprint 1 + Sprint 2)
- **Lam Chin Yui:** Product Backlog, Partial Domain Model
- **Lai Tsz Ng:** Communications, UI Storyboards, Source Code
- **Wang Yam Yuk:** UI Storyboards, Source Code
- **Kumar Tvesha Sanjay:** Product Backlog, Partial Domain Model

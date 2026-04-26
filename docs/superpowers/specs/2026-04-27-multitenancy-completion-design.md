# BetaTrax Sprint 3 — Sub-project 3: Multi-tenancy Completion (Tier A)

**Date:** 2026-04-27
**Author:** Claude (brainstormed with dalight-luckyw)
**Status:** Approved for planning
**Scope:** Sub-project 3 of 4 in Sprint 3. Brings the partially-wired django-tenants integration to a runnable, demonstrable state on a fresh local PostgreSQL — without restructuring the BTAPI app or resetting migrations. See §11 for the limitations this Tier-A scope deliberately accepts.

This sub-project depends on Postgres being installed and running locally (Postgres.app v18 or equivalent).

## 1. Background

Sprint 3 §14-17 requires BetaTrax to support multiple tenants — each one a separate development company sharing a single PostgreSQL database via the *single-database, separate-schema* pattern provided by `django-tenants`. The team has already taken the foundational steps:

- `django-tenants==3.10.1` and `psycopg2-binary==2.9.12` are in `requirements.txt`.
- `BTConfig/settings.py` configures `SHARED_APPS`, `TENANT_APPS`, the `django_tenants.postgresql_backend` engine, `TenantMainMiddleware`, `TENANT_MODEL='BTAPI.Client'`, and `DATABASE_ROUTERS=('django_tenants.routers.TenantSyncRouter',)`.
- `BTAPI/models.py` defines `Client(TenantMixin)` (with `auto_create_schema=True`) and `Domain(DomainMixin)`.
- `BTAPI/admin.py` auto-registers all models, so `Client` and `Domain` are visible in `/admin/`.

What is *not* yet done:

- Postgres has no `btpostgres` database and no `admin` user — settings.py's literal credentials cannot connect.
- No tenant has been bootstrapped. There is no public tenant, no demo tenants, no domains. The router has nothing to route.
- Migrations have not been re-run via `migrate_schemas`; previous `migrate` commands targeted the (now superseded) SQLite database.
- README does not document the Postgres + tenants setup workflow.
- There is no demo data showing tenant isolation.

This spec delivers a Tier-A finish: minimal changes to source code (only a new management command), comprehensive setup documentation, and demonstrable per-tenant data isolation across two demo tenants. Architectural cleanups (splitting BTAPI into shared + tenant apps, squashing migrations) are explicitly deferred.

## 2. Goals

1. Establish a working local Postgres environment matching `settings.py`'s credentials.
2. Apply migrations cleanly via `migrate_schemas` to both the public schema and tenant schemas.
3. Provide a single bootstrap command that creates the public tenant, two demo tenants (`acme` and `globex`), their domains, and a small data fixture in each.
4. Demonstrate isolation: a request to `acme.localhost:8000` sees only ACME's data; a request to `globex.localhost:8000` sees only Globex's.
5. Document the entire workflow in README so the grader (and future contributors) can reproduce it from a fresh clone.
6. Preserve the 16 passing tests from sub-projects 1 + 2.

## 3. Non-goals

- Splitting `BTAPI` into a shared `BTTenants` app + a tenant `BTAPI` app (Tier B).
- Squashing or resetting the 50-file migration history (Tier C).
- Tenant-aware automated tests under Postgres (would require Postgres in CI; current test suite intentionally strips tenants and uses SQLite).
- Tenant self-service signup endpoint, branding, theming, deletion, or backup tooling.
- Modifying `BTAPI/views.py`, `BTAPI/serializer.py`, `BTAPI/urls.py`, or any existing model — the views are tenant-agnostic and continue to work because TenantSyncRouter handles schema selection at the ORM level.

## 4. Postgres environment setup

These commands run once on a freshly-installed Postgres.app v18. They are documented in the README so the grader can replicate the environment.

### 4.1 Make Postgres CLI tools available

Postgres.app installs `psql`, `createuser`, `createdb`, `pg_isready` etc. under `/Applications/Postgres.app/Contents/Versions/latest/bin/`. They are not on PATH by default.

For the current shell session:

```bash
export PATH="/Applications/Postgres.app/Contents/Versions/latest/bin:$PATH"
```

For a persistent setup the user appends that line to `~/.zshrc`. The README mentions both options.

### 4.2 Create the role and database

```bash
createuser --superuser admin
psql -d postgres -c "ALTER USER admin WITH PASSWORD 'password';"
createdb -O admin btpostgres
```

The `--superuser` flag is required because `django-tenants` issues `CREATE SCHEMA` statements at runtime (when `auto_create_schema=True` clients are saved). On Postgres, `CREATE SCHEMA` requires either superuser or explicit `CREATE` privilege on the database; superuser is simpler for a school-project local environment.

The credentials match `BTConfig/settings.py` literals — no settings change needed.

### 4.3 Verify connectivity

```bash
psql -d btpostgres -U admin -c '\conninfo'
```

Expected: `You are connected to database "btpostgres" as user "admin"...`. If this fails, the pg_hba.conf may need a `local all admin md5` line — Postgres.app's default trust auth on localhost should make this unnecessary.

## 5. Migrations

`django-tenants` replaces Django's `migrate` command with `migrate_schemas`. There are two phases:

```bash
python3 manage.py migrate_schemas --shared    # public schema only
python3 manage.py migrate_schemas             # every tenant schema (initially zero, so a no-op)
```

The first command applies migrations from `SHARED_APPS` (`django_tenants`, `BTAPI`, `rest_framework`, `django.contrib.{admin,auth,contenttypes,sessions,messages,staticfiles}`) to the `public` schema. After this command, the public schema contains:

- Tenant metadata tables: `BTAPI_client`, `BTAPI_domain`.
- Auth tables: `auth_user`, `auth_group`, `auth_permission`, ...
- All BTAPI data-model tables: `BTAPI_developer`, `BTAPI_product`, `BTAPI_defectreport`, `BTAPI_comment` — these are created here as a side effect of `BTAPI` being in `SHARED_APPS`. They are unused in normal operation (TenantSyncRouter will direct reads/writes to the per-tenant schemas) but are not harmful.

The second command iterates all rows of the tenant table (initially zero) and applies `TENANT_APPS` migrations to each. After §6 bootstraps the tenants, this command will rerun automatically during `Client.objects.create(...)` thanks to `auto_create_schema=True`, so explicit invocation after bootstrap is not required.

## 6. Bootstrap management command

### 6.1 File: `BTAPI/management/commands/bootstrap_tenants.py`

A Django management command that creates the public tenant, two demo tenants, their domains, the standard groups, sample users in each tenant, and one product + one defect report per tenant.

The command is idempotent: re-running it does not duplicate rows. It uses `get_or_create` for tenants, domains, and groups; for users, it skips creation if the username already exists; for products and defect reports, it skips creation if the tenant schema already has any defect report.

### 6.2 Created tenants

| Tenant name | `schema_name` | Domain | Sample data summary |
|---|---|---|---|
| Public | `public` | `localhost` | None — only tenant metadata. The public schema is for admin use (creating new tenants, managing global state). |
| ACME Corp | `acme` | `acme.localhost` | Groups (User/Developer/Owner); users `AcmePo`, `AcmeDev`, `AcmeTester`; product `AcmeProd1`; defect report `AcmeDef1`. |
| Globex | `globex` | `globex.localhost` | Groups (User/Developer/Owner); users `GlobexPo`, `GlobexDev`, `GlobexTester`; product `GlobexProd1`; defect report `GlobexDef1`. |

All sample-user passwords are `pw` (matching the test fixture convention from sub-project 2; documented in README; not a security concern for local demo).

### 6.3 Schema-switching strategy

To create per-tenant data inside a tenant's schema, the command uses `django_tenants.utils.tenant_context`:

```python
from django_tenants.utils import tenant_context

with tenant_context(client):
    Group.objects.get_or_create(name='Developer')
    User.objects.create_user(...)
    # ... etc
```

`tenant_context` switches the active schema for the duration of the `with` block, so all ORM operations inside it write to the tenant's schema rather than public.

### 6.4 Domain rows

```python
Domain.objects.get_or_create(
    domain='acme.localhost',
    defaults={'tenant': acme_client, 'is_primary': True},
)
```

`is_primary=True` is what `TenantMainMiddleware` looks up when matching the request `Host` header. macOS resolves `*.localhost` to `127.0.0.1` by default, so no `/etc/hosts` edit is required.

### 6.5 Run

```bash
python3 manage.py bootstrap_tenants
```

Expected output (first run, summarised):

```
Creating tenant 'Public' (schema=public, domain=localhost) ...
Creating tenant 'ACME Corp' (schema=acme, domain=acme.localhost) ...
  Loaded 3 groups
  Created users: AcmePo, AcmeDev, AcmeTester
  Created product 'AcmeProd1' and defect 'AcmeDef1'
Creating tenant 'Globex' (schema=globex, domain=globex.localhost) ...
  Loaded 3 groups
  Created users: GlobexPo, GlobexDev, GlobexTester
  Created product 'GlobexProd1' and defect 'GlobexDef1'
Bootstrap complete.
```

Re-running prints `already exists, skipping` for each tenant and each user.

## 7. Superuser for the public schema

```bash
python3 manage.py createsuperuser
```

`django-tenants` defaults `createsuperuser` to the public schema, which is correct — the public admin is where the team manages tenants. (Each tenant can later get its own superuser via `python3 manage.py tenant_command createsuperuser --schema=<schema>` if needed; not required for the demo.)

## 8. Demo / acceptance verification

After §4 + §5 + §6 + §7 are run, the following must hold:

### 8.1 Schemas exist

```bash
psql -d btpostgres -U admin -c '\dn'
```

Lists at least: `public`, `acme`, `globex`. (Postgres-internal schemas like `information_schema` will also appear; that is normal.)

### 8.2 Public admin shows tenants

```
http://localhost:8000/admin/   # log in as the §7 superuser
```

The admin index lists `Clients` and `Domains` (under the BTAPI section). Clicking through shows three Client rows and three Domain rows.

### 8.3 Tenant routing works (the key isolation test)

Start the dev server:

```bash
python3 manage.py runserver
```

Then:

```bash
# Acquire a token in the ACME tenant
curl -s -X POST http://acme.localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"AcmePo","password":"pw"}'
# Expected: 200 with access + refresh tokens

# Same call against the Globex tenant for the same user — must fail
curl -s -X POST http://globex.localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"AcmePo","password":"pw"}'
# Expected: 401 — AcmePo does not exist in the globex schema's auth_user table
```

A successful 200 followed by a 401 proves data is isolated per tenant.

### 8.4 Tenant data is isolated

```bash
# In the same shell, with an AcmePo access token in $ACME_TOKEN:
curl -s -H "Authorization: Bearer $ACME_TOKEN" \
  http://acme.localhost:8000/api/reports/ALL/
# Expected: list contains 'AcmeDef1', does NOT contain 'GlobexDef1'

# After acquiring a GlobexPo token in $GLOBEX_TOKEN:
curl -s -H "Authorization: Bearer $GLOBEX_TOKEN" \
  http://globex.localhost:8000/api/reports/ALL/
# Expected: list contains 'GlobexDef1', does NOT contain 'AcmeDef1'
```

### 8.5 Existing tests still pass

```bash
python3 manage.py test --settings=BTConfig.settings_test BTAPI
```

Expected: `Ran 16 tests in 1.XXXs · OK`. Tests run on SQLite as before (sub-project 1's `settings_test` strips `django_tenants`). This is unchanged by sub-project 3.

## 9. README updates

A new "Multi-tenancy setup" section is added between the existing "Setup & Installation" and "Testing & Coverage" sections. Contents:

1. Postgres install pointer (Postgres.app or Homebrew + a one-line link).
2. Adding the Postgres bin directory to PATH (current-shell + persistent variants).
3. The four-line role + database creation block (§4.2).
4. Optional `psql -d btpostgres -U admin -c '\conninfo'` connectivity verification.
5. The two `migrate_schemas` commands (§5).
6. The `bootstrap_tenants` command (§6) with a one-line description.
7. The `createsuperuser` step (§7).
8. The verification curls from §8.3 and §8.4 as a "Verify the demo works" subsection.
9. A "Limitations" subsection mirroring §11 below.

## 10. Acceptance criteria (consolidation)

1. ✅ `psql -d btpostgres -U admin -c '\dn'` lists `public`, `acme`, `globex`.
2. ✅ `python3 manage.py runserver` starts cleanly with no migration warnings or errors.
3. ✅ `curl -X POST http://acme.localhost:8000/api/token/ -d '{"username":"AcmePo","password":"pw"}'` returns 200 with both `access` and `refresh` tokens.
4. ✅ The same call against `http://globex.localhost:8000/api/token/` returns 401 (AcmePo doesn't exist in the globex schema).
5. ✅ `GET /api/reports/ALL/` against `acme.localhost` lists `AcmeDef1` and not `GlobexDef1`. Reverse holds for `globex.localhost`.
6. ✅ `http://localhost:8000/admin/` shows the three Clients and Domains in the public admin.
7. ✅ All 16 existing tests still pass under `settings_test`.
8. ✅ README documents the entire setup workflow end-to-end and the three known limitations.

## 11. Known limitations (logged in README)

1. **`BTAPI` app is dual-listed in `SHARED_APPS` and `TENANT_APPS`.** Effect: the per-tenant data tables (`BTAPI_developer`, `BTAPI_product`, `BTAPI_defectreport`, `BTAPI_comment`) get created in *both* the public schema and every tenant schema. Per-tenant isolation still works because `TenantSyncRouter` directs ORM reads/writes to the active schema — the public-schema copies of these tables are unused shadow tables. A future cleanup would split `BTAPI` into a tiny `BTTenants` app for `Client`/`Domain` (Tier B in the brainstorm).
2. **Test suite does not exercise tenant isolation.** `BTConfig/settings_test.py` strips `django_tenants` from `INSTALLED_APPS` / `MIDDLEWARE` and runs on in-memory SQLite, so the 16 tests do not validate that tenant routing is correct. A second test pass under the real Postgres + tenants config would be needed to fully validate.
3. **Migration history not squashed.** All 50 BTAPI migrations from the SQLite era are replayed as-is into Postgres. Some are likely redundant (alter-then-revert sequences). Cleanup is out of scope for Sprint 3.

These are honest disclosures, not blockers — the demo proves multi-tenancy works for the actual API surface.

# Multi-tenancy Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver Sprint 3 sub-project 3 (Tier A) — bring django-tenants from configured-but-unused to a runnable, demonstrable multi-tenant deployment on local PostgreSQL, with two demo tenants (`acme` and `globex`) showing isolated data.

**Architecture:** Add no view code. Add one Django management command (`bootstrap_tenants`) that idempotently creates the public tenant, two demo tenants with their domains, and per-tenant sample data using `django_tenants.utils.tenant_context` for schema switching. All other work is shell-driven Postgres setup and README documentation.

**Tech Stack:** PostgreSQL 18 (via Postgres.app), `django-tenants==3.10.1`, `psycopg2-binary==2.9.12`, Django 6.0.3.

**Design spec:** `docs/superpowers/specs/2026-04-27-multitenancy-completion-design.md`

**Important:** Several steps in this plan run *destructive or environment-mutating shell commands* (creating Postgres roles/databases, applying migrations, creating tenants). If any step fails, STOP and report — do not retry blindly.

---

## Pre-flight

- [ ] **Pre-flight Step 1: Verify Postgres is running and the bin directory exists**

```bash
ls /Applications/Postgres.app/Contents/Versions/latest/bin/psql
pgrep -lf 'postgres -D' | head -1
```

Expected: the `psql` binary exists; one `postgres` process is listed. If either fails, the user must launch Postgres.app and confirm the server is running on port 5432 before continuing.

- [ ] **Pre-flight Step 2: Add Postgres bin to PATH for this session**

```bash
export PATH="/Applications/Postgres.app/Contents/Versions/latest/bin:$PATH"
psql --version
```

Expected: `psql (PostgreSQL) 18.X`. Note: this PATH change is session-only. The README documents the persistent (`~/.zshrc`) variant.

- [ ] **Pre-flight Step 3: Verify the venv is active and `django-tenants` is importable**

```bash
source venv/bin/activate
python3 -c "import django_tenants; print('django-tenants installed at', django_tenants.__file__)"
```

Expected: a path under `venv/lib/python3.14/site-packages/django_tenants/__init__.py`.

- [ ] **Pre-flight Step 4: Capture the current test pass count (regression baseline)**

```bash
python3 manage.py test --settings=BTConfig.settings_test BTAPI 2>&1 | grep -E '^Ran '
```

Expected: `Ran 16 tests in 1.XXXs`. We must preserve this at the end.

---

## Task 1: Create Postgres role and database

This task uses the macOS shell user's Postgres.app default trust auth. If the role / database already exist (from a previous run), the commands will print informational errors that are safe to ignore.

- [ ] **Step 1: Create the `admin` role**

```bash
createuser --superuser admin || echo "(role already exists, continuing)"
```

Expected: empty output on first run; the `(role already exists, continuing)` echo on subsequent runs.

- [ ] **Step 2: Set the role's password to match `settings.py`**

```bash
psql -d postgres -c "ALTER USER admin WITH PASSWORD 'password';"
```

Expected: `ALTER ROLE`.

- [ ] **Step 3: Create the `btpostgres` database owned by `admin`**

```bash
createdb -O admin btpostgres || echo "(database already exists, continuing)"
```

Expected: empty output on first run; the `(database already exists, continuing)` echo on subsequent runs.

- [ ] **Step 4: Verify connectivity using the project's credentials**

```bash
PGPASSWORD=password psql -h localhost -U admin -d btpostgres -c '\conninfo'
```

Expected: a line beginning with `You are connected to database "btpostgres" as user "admin"`. If this fails with `password authentication failed`, the user must check Postgres.app's `pg_hba.conf` allows password auth for `admin` on localhost — STOP and report.

(No commit; this task only mutates Postgres state, no files change.)

---

## Task 2: Apply shared migrations to the public schema

This applies the `SHARED_APPS` migrations (django_tenants + BTAPI + DRF + Django built-ins) to the `public` schema. After this, all auth/admin/BTAPI tables exist in `public`.

- [ ] **Step 1: Run `migrate_schemas --shared`**

```bash
python3 manage.py migrate_schemas --shared 2>&1 | tail -20
```

Expected: many lines like `  Applying BTAPI.0001_initial... OK`, ending with `Applying ...XXXX_some_migration... OK` lines — no errors. If any migration fails, STOP and report — Tier-A scope assumes migrations apply cleanly because they did so previously (see commit `ec738a3 init migrate to postgres`).

- [ ] **Step 2: Verify the public schema has the expected tables**

```bash
PGPASSWORD=password psql -h localhost -U admin -d btpostgres -c "\dt public.*" | head -30
```

Expected: at least these tables visible: `BTAPI_client`, `BTAPI_domain`, `BTAPI_developer`, `BTAPI_product`, `BTAPI_defectreport`, `BTAPI_comment`, `auth_user`, `auth_group`, `auth_permission`. (The `BTAPI_developer` etc. are the unused public-schema shadow tables described in the spec §11 limitation #1 — that is expected.)

- [ ] **Step 3: Run the empty `migrate_schemas` (no tenants yet → no-op)**

```bash
python3 manage.py migrate_schemas 2>&1 | tail -5
```

Expected: a short summary indicating zero tenant schemas processed.

(No commit; this task only mutates DB state.)

---

## Task 3: Create the bootstrap_tenants management command

Add the management-command package and the bootstrap script. Do not run it yet — Task 4 verifies discoverability, Task 5 runs it.

**Files:**
- Create: `BTAPI/management/__init__.py`
- Create: `BTAPI/management/commands/__init__.py`
- Create: `BTAPI/management/commands/bootstrap_tenants.py`

- [ ] **Step 1: Create the empty package marker files**

```bash
mkdir -p BTAPI/management/commands
touch BTAPI/management/__init__.py
touch BTAPI/management/commands/__init__.py
```

Expected: both files exist (empty). Django requires these for management-command discovery.

- [ ] **Step 2: Create `BTAPI/management/commands/bootstrap_tenants.py`**

Write the file with these exact contents:

```python
from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django_tenants.utils import tenant_context

from BTAPI.models import Client, DefectReport, Developer, Domain, Product


TENANTS = [
    {
        'schema_name': 'public',
        'name': 'Public',
        'domain': 'localhost',
        'sample_data': False,
    },
    {
        'schema_name': 'acme',
        'name': 'ACME Corp',
        'domain': 'acme.localhost',
        'sample_data': True,
        'prefix': 'Acme',
    },
    {
        'schema_name': 'globex',
        'name': 'Globex',
        'domain': 'globex.localhost',
        'sample_data': True,
        'prefix': 'Globex',
    },
]


class Command(BaseCommand):
    help = (
        "Bootstrap the public tenant plus two demo tenants (ACME, Globex) "
        "with isolated sample data.  Idempotent: safe to re-run."
    )

    def handle(self, *args, **options):
        for cfg in TENANTS:
            client = self._get_or_create_tenant(cfg)
            self._get_or_create_domain(cfg, client)
            if cfg['sample_data']:
                self._populate_sample_data(client, cfg['prefix'])
        self.stdout.write(self.style.SUCCESS('Bootstrap complete.'))

    def _get_or_create_tenant(self, cfg):
        client, created = Client.objects.get_or_create(
            schema_name=cfg['schema_name'],
            defaults={'name': cfg['name']},
        )
        action = 'Creating' if created else 'Skipping (exists)'
        self.stdout.write(
            f"{action} tenant '{cfg['name']}' "
            f"(schema={cfg['schema_name']}, domain={cfg['domain']})"
        )
        return client

    def _get_or_create_domain(self, cfg, client):
        Domain.objects.get_or_create(
            domain=cfg['domain'],
            defaults={'tenant': client, 'is_primary': True},
        )

    def _populate_sample_data(self, client, prefix):
        with tenant_context(client):
            user_group, _ = Group.objects.get_or_create(name='User')
            dev_group, _ = Group.objects.get_or_create(name='Developer')
            owner_group, _ = Group.objects.get_or_create(name='Owner')

            if DefectReport.objects.exists():
                self.stdout.write(
                    f"  Sample data already exists in {prefix}, skipping"
                )
                return

            po = User.objects.create_user(
                username=f'{prefix}Po', password='pw',
                email=f'po@{prefix.lower()}.example.com',
            )
            po.groups.add(owner_group)

            dev = User.objects.create_user(
                username=f'{prefix}Dev', password='pw',
                email=f'dev@{prefix.lower()}.example.com',
            )
            dev.groups.add(dev_group)

            tester = User.objects.create_user(
                username=f'{prefix}Tester', password='pw',
                email=f'tester@{prefix.lower()}.example.com',
            )
            tester.groups.add(user_group)

            Developer.objects.create(
                user=dev, fixedCount=0, reopenedCount=0,
            )

            product = Product.objects.create(
                id=f'{prefix}Prod1',
                displayName=f'{prefix} Demo Product',
                description=f'{prefix} demo description',
                currentVersion='1.0',
                isActiveBeta=True,
                ownerId=po,
                devId=dev,
            )

            DefectReport.objects.create(
                id=f'{prefix}Def1',
                productId=product,
                productVersion='1.0',
                title=f'{prefix} sample defect',
                description='Sample defect for demo.',
                reproductionSteps='1. Open app  2. See bug',
                testerId=tester,
                status=DefectReport.Status.NEW,
                assignedToId=dev,
            )

            self.stdout.write(
                f"  Created users: {prefix}Po, {prefix}Dev, {prefix}Tester"
            )
            self.stdout.write(
                f"  Created product '{prefix}Prod1' and defect '{prefix}Def1'"
            )
```

- [ ] **Step 3: Verify Django discovers the command**

```bash
python3 manage.py help bootstrap_tenants 2>&1 | head -10
```

Expected: a usage block that includes the help string `"Bootstrap the public tenant plus two demo tenants ..."`. If you instead see `Unknown command: 'bootstrap_tenants'`, the package files in Step 1 are missing or empty — recheck.

- [ ] **Step 4: Commit the management command**

```bash
git add BTAPI/management
git commit --only \
    BTAPI/management/__init__.py \
    BTAPI/management/commands/__init__.py \
    BTAPI/management/commands/bootstrap_tenants.py \
    -m "feat(tenants): add bootstrap_tenants management command

Idempotent command that creates the public tenant plus two demo
tenants (ACME, Globex) with their domains and isolated per-tenant
sample data (groups, three role users, a Product, a DefectReport).
Uses django_tenants.utils.tenant_context to switch schemas during
data creation."
```

---

## Task 4: Run bootstrap_tenants and verify schemas

- [ ] **Step 1: Run the bootstrap command**

```bash
python3 manage.py bootstrap_tenants
```

Expected output (first run):

```
Creating tenant 'Public' (schema=public, domain=localhost)
Creating tenant 'ACME Corp' (schema=acme, domain=acme.localhost)
=== Running migrate for schema acme
... many migration apply lines ...
  Created users: AcmePo, AcmeDev, AcmeTester
  Created product 'AcmeProd1' and defect 'AcmeDef1'
Creating tenant 'Globex' (schema=globex, domain=globex.localhost)
=== Running migrate for schema globex
... many migration apply lines ...
  Created users: GlobexPo, GlobexDev, GlobexTester
  Created product 'GlobexProd1' and defect 'GlobexDef1'
Bootstrap complete.
```

The "Running migrate for schema X" lines come from `auto_create_schema=True` on `Client` — django-tenants automatically runs `TENANT_APPS` migrations for each new tenant schema.

If any migration in this auto-run fails (an error mid-output), STOP and report. Possible cause: a migration in `BTAPI/migrations/` that depends on data from the old SQLite era — Tier-B scope would address this, Tier-A does not.

- [ ] **Step 2: Verify the schemas exist**

```bash
PGPASSWORD=password psql -h localhost -U admin -d btpostgres -c '\dn'
```

Expected: the output lists `public`, `acme`, `globex` (plus Postgres-internal schemas like `information_schema`).

- [ ] **Step 3: Verify the per-tenant data tables exist in tenant schemas**

```bash
PGPASSWORD=password psql -h localhost -U admin -d btpostgres -c "\dt acme.*" | head -15
```

Expected: tables include `BTAPI_developer`, `BTAPI_product`, `BTAPI_defectreport`, `BTAPI_comment`, `auth_user`, `auth_group`. The `BTAPI_client` and `BTAPI_domain` tables should NOT appear here (they live in public only).

- [ ] **Step 4: Verify sample data is in the tenant schemas**

```bash
PGPASSWORD=password psql -h localhost -U admin -d btpostgres -c \
    "SET search_path TO acme; SELECT id, title FROM \"BTAPI_defectreport\";"
PGPASSWORD=password psql -h localhost -U admin -d btpostgres -c \
    "SET search_path TO globex; SELECT id, title FROM \"BTAPI_defectreport\";"
```

Expected: the first command prints one row with id `AcmeDef1`. The second prints one row with id `GlobexDef1`. Each tenant has its OWN defect — that is the isolation proof at the SQL level.

- [ ] **Step 5: Verify idempotency by re-running the command**

```bash
python3 manage.py bootstrap_tenants 2>&1 | tail -10
```

Expected: every line begins with `Skipping (exists)` for tenants and `Sample data already exists in X, skipping` for ACME and Globex. No new rows are created.

(No commit; this task only mutates DB state.)

---

## Task 5: Create the public-schema superuser

This step is interactive — the user must type a username, email (optional), and password at the prompts.

- [ ] **Step 1: Run createsuperuser**

```bash
python3 manage.py createsuperuser
```

Expected: prompts for `Username:`, `Email address:`, `Password:`, `Password (again):`. After completion, the message `Superuser created successfully.` appears.

`django-tenants` defaults this command to the public schema, which is the correct place — public is where the team manages tenants.

(No commit; user state in DB.)

---

## Task 6: Demo verification (the isolation proof)

Start the dev server and exercise the API across two tenants. This is the Sprint 3 §38-equivalent grading-level demo.

- [ ] **Step 1: Start the dev server in the background**

```bash
python3 manage.py runserver 0.0.0.0:8000 > /tmp/runserver.log 2>&1 &
RUNSERVER_PID=$!
sleep 2
echo "runserver started as PID $RUNSERVER_PID"
```

Expected: a PID is printed. Check `/tmp/runserver.log` if anything went wrong.

- [ ] **Step 2: Acquire an ACME tenant token (must succeed)**

```bash
ACME_TOKEN=$(curl -s -X POST http://acme.localhost:8000/api/token/ \
    -H "Content-Type: application/json" \
    -d '{"username":"AcmePo","password":"pw"}' \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["access"])')
echo "ACME token (first 40 chars): ${ACME_TOKEN:0:40}..."
test -n "$ACME_TOKEN" && echo "OK" || echo "FAIL — no token returned"
```

Expected: a JWT prefix is printed, and `OK`. If `FAIL`, check `/tmp/runserver.log` and stop.

- [ ] **Step 3: Confirm cross-tenant rejection**

```bash
curl -s -o /dev/null -w "%{http_code}\n" \
    -X POST http://globex.localhost:8000/api/token/ \
    -H "Content-Type: application/json" \
    -d '{"username":"AcmePo","password":"pw"}'
```

Expected: `401`. AcmePo does not exist in the globex schema's `auth_user` table. A `401` here is the proof of auth-table isolation.

- [ ] **Step 4: Confirm data isolation via list endpoint**

```bash
echo "=== ACME's reports ==="
curl -s -H "Authorization: Bearer $ACME_TOKEN" \
    http://acme.localhost:8000/api/reports/ALL/ \
    | python3 -m json.tool

GLOBEX_TOKEN=$(curl -s -X POST http://globex.localhost:8000/api/token/ \
    -H "Content-Type: application/json" \
    -d '{"username":"GlobexPo","password":"pw"}' \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["access"])')

echo "=== Globex's reports ==="
curl -s -H "Authorization: Bearer $GLOBEX_TOKEN" \
    http://globex.localhost:8000/api/reports/ALL/ \
    | python3 -m json.tool
```

Expected:
- The first list contains exactly one item with `id == "AcmeDef1"`.
- The second list contains exactly one item with `id == "GlobexDef1"`.
- Neither list contains the other tenant's defect.

If either list contains both defects, tenant isolation is broken — STOP and report. If either list is empty, the bootstrap data may not have been written into the right schema.

- [ ] **Step 5: Stop the dev server**

```bash
kill $RUNSERVER_PID 2>/dev/null
wait $RUNSERVER_PID 2>/dev/null
echo "runserver stopped"
```

Expected: `runserver stopped`. If the variable lookup fails (because the shell session was reset), use `pgrep -f 'manage.py runserver' | xargs kill` to clean up.

(No commit; this task only validates runtime behaviour.)

---

## Task 7: Update the README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Locate the insertion point**

```bash
grep -n '^## ' README.md
```

The new "Multi-tenancy setup" section goes immediately after the existing "Setup & Installation" section and before "Testing & Coverage".

- [ ] **Step 2: Insert the section**

Read the README, find the line `## Testing & Coverage`, and insert the following block immediately *before* it (preserve all surrounding content):

````markdown
## Multi-tenancy Setup (PostgreSQL + django-tenants)

BetaTrax is configured for the *single-database, separate-schema* multi-tenancy pattern via [`django-tenants`](https://django-tenants.readthedocs.io/). Each customer (a development company) gets its own PostgreSQL schema; the API routes requests to the right schema based on the request's hostname.

### 1. Install PostgreSQL

Either:
- **Postgres.app** — download from [postgresapp.com](https://postgresapp.com/) and launch.  Server runs on `localhost:5432` by default.
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

The credentials match `BTConfig/settings.py`. The `--superuser` flag is required because django-tenants needs to issue `CREATE SCHEMA` at runtime.

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

Visit `http://localhost:8000/admin/` to manage tenants and domains.

### 7. Verify the demo works

Start the dev server:

```bash
python3 manage.py runserver
```

Then in another terminal:

```bash
# Acquire a token in ACME — must succeed
curl -X POST http://acme.localhost:8000/api/token/ \
    -H "Content-Type: application/json" \
    -d '{"username":"AcmePo","password":"pw"}'

# Same user, Globex tenant — must fail with 401 (user does not exist there)
curl -X POST http://globex.localhost:8000/api/token/ \
    -H "Content-Type: application/json" \
    -d '{"username":"AcmePo","password":"pw"}'

# Per-tenant data isolation — each list contains only its own defect
curl -H "Authorization: Bearer <ACME_ACCESS_TOKEN>" \
    http://acme.localhost:8000/api/reports/ALL/
curl -H "Authorization: Bearer <GLOBEX_ACCESS_TOKEN>" \
    http://globex.localhost:8000/api/reports/ALL/
```

`*.localhost` resolves to `127.0.0.1` automatically on macOS — no `/etc/hosts` edit is required.

### Limitations

1. The `BTAPI` app is dual-listed in `SHARED_APPS` and `TENANT_APPS`.  Effect: per-tenant data tables (`Developer`, `Product`, `DefectReport`, `Comment`) get created in *both* the public schema and every tenant schema.  Per-tenant isolation still works correctly because `TenantSyncRouter` directs reads/writes to the active schema, but the public-schema copies are unused shadow tables.  A future cleanup would split `BTAPI` into a `BTTenants` app for `Client`/`Domain` plus a tenant-only `BTAPI`.
2. The automated test suite (`BTConfig.settings_test`) strips `django_tenants` and runs on in-memory SQLite, so it does not exercise tenant isolation.  A second test pass under the real Postgres + tenants config is required for full validation.
3. The migration history (50 BTAPI migrations from the SQLite era) was not squashed.  Some migrations are likely redundant.  Cleanup is out of scope for Sprint 3.
````

- [ ] **Step 3: Commit**

```bash
git commit --only README.md -m "docs(readme): add Multi-tenancy Setup section

Documents Postgres install, role/database creation, migrate_schemas
workflow, bootstrap_tenants command, demo verification curls, and
the three known Tier-A limitations."
```

---

## Task 8: Final verification

- [ ] **Step 1: Confirm 16 tests still pass (no regression from sub-projects 1+2)**

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

- [ ] **Step 3: Confirm git history**

```bash
git log --oneline -8
```

Expected (most recent first):

```
docs(readme): add Multi-tenancy Setup section
feat(tenants): add bootstrap_tenants management command
docs: add Sprint 3 sub-project 3 design (multi-tenancy completion, Tier A)
... (sub-project 2 commits)
```

- [ ] **Step 4: Confirm working tree is clean**

```bash
git status --short
```

Expected: empty output.

- [ ] **Step 5: Sanity-check schema list**

```bash
PGPASSWORD=password psql -h localhost -U admin -d btpostgres -c '\dn' | grep -E '(public|acme|globex)'
```

Expected: three lines, one each for `public`, `acme`, `globex`.

---

## Acceptance criteria (from spec §10)

1. ✅ `psql ... -c '\dn'` lists `public`, `acme`, `globex` → Task 4 Step 2, Task 8 Step 5.
2. ✅ `python3 manage.py runserver` starts cleanly → Task 6 Step 1.
3. ✅ `POST http://acme.localhost:8000/api/token/` for AcmePo returns 200 → Task 6 Step 2.
4. ✅ Same call against `globex.localhost` returns 401 → Task 6 Step 3.
5. ✅ ACME's reports list contains AcmeDef1 only; Globex's contains GlobexDef1 only → Task 6 Step 4.
6. ✅ Public admin shows three Clients and Domains → manual verification at end of Task 5 (browser-based; not automated).
7. ✅ All 16 existing tests still pass → Task 8 Step 1.
8. ✅ README documents the entire workflow and limitations → Task 7.

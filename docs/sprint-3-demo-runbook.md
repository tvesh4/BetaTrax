# Sprint 3 Demo Runbook — BetaTrax (Group F)

A step-by-step script for the final review and demo with the management team. Total target runtime: **20–25 min** of demo + Q&A.

The four Sprint 3 deliverables, in the order we will present them:

1. **Multi-tenancy** (`django-tenants` + PostgreSQL)
2. **API documentation** (`drf-spectacular` Swagger UI / ReDoc)
3. **Automated endpoint tests** (13 endpoint tests — one happy-path per endpoint method, plus three role-gate / terminal-state cases)
4. **Developer effectiveness metric** (`BTAPI/metrics.py` + 100% statement & branch coverage)

This order tells a story: *we set up the multi-tenant backbone → we documented every endpoint → we automated tests against them → we pinned full coverage on the new business-logic module.*

---

## 0. Pre-demo checklist (do this the morning of, then 5 min before)

Run through this **once the morning of** to catch any environment drift, then **once 5 min before** in the actual demo terminal.

### 0.1  Working environment

```bash
cd /Users/wangyamyuk13/Documents/GitHub/BetaTrax
git checkout dev
git pull origin dev          # confirm everyone is on the latest commit
source venv/bin/activate
python3 -c "import django, django_tenants, drf_spectacular, coverage; print('imports OK')"
```

If `python3 -c "import …"` fails: `pip install -r requirements.txt`.

### 0.2  PostgreSQL is up and reachable

```bash
PGPASSWORD=password psql -h localhost -U admin -d btpostgres -c '\conninfo'
```

If `psql` is not on PATH (Postgres.app users):

```bash
export PATH="/Applications/Postgres.app/Contents/Versions/latest/bin:$PATH"
```

If the database/role does not exist, follow **README.md → Multi-tenancy Setup → §3 Create the role and database**.

### 0.3  Schemas migrated and tenants bootstrapped

```bash
python3 manage.py migrate_schemas --shared
python3 manage.py migrate_schemas
python3 manage.py bootstrap_tenants     # idempotent — safe to re-run
```

Expected last line: `Bootstrap complete.`

Confirm three tenants exist:

```bash
PGPASSWORD=password psql -h localhost -U admin -d btpostgres \
    -c 'SELECT schema_name, name FROM public."BTAPI_client" ORDER BY schema_name;'
```

You should see `public`, `se1`, `se2`.

### 0.4  Smoke-test all four demo segments end-to-end (most important step)

In **a single dry run**, walk every command in §1 → §4 below. If anything fails, fix it now — not in front of the room.

### 0.5  Terminal & browser layout

Open **three terminal panes** (tmux/iTerm split):

| Pane | Purpose | Pre-set command |
|---|---|---|
| **A** (top) | Dev server | `python3 manage.py runserver` (don't start yet) |
| **B** (middle) | curl / psql | empty |
| **C** (bottom) | Tests + coverage | empty |

Open **four browser tabs**, in this order:

1. `http://se1.localhost:8000/api/schema/swagger-ui/`
2. `http://se1.localhost:8000/api/schema/redoc/`
3. `http://localhost:8000/admin/` (leave on the login page)
4. *(optional)* `http://se2.localhost:8000/api/schema/swagger-ui/` — to show docs are tenant-agnostic

Have **one Postman window** open with the collection from `postman/collections/` loaded as a backup if Swagger misbehaves.

### 0.6  Start the dev server in pane A

```bash
python3 manage.py runserver
```

Leave it running for the rest of the demo.

---

## 1. Multi-tenancy (≈ 6 min)

### 1.1  Frame the problem (30 s)

> "In Sprint 1 and 2 the system was single-tenant — one database, one customer's worth of data. Sprint 3 §15–§21 asked us to support multiple beta-testing companies on the same deployment, with strict data isolation. We chose `django-tenants` with one PostgreSQL schema per tenant — strong isolation at the database layer, single-database operational simplicity."

Open `BTConfig/settings.py` briefly and point to:
- `SHARED_APPS` vs `TENANT_APPS` (lines 34–51)
- `DATABASES` engine `django_tenants.postgresql_backend` (line 98)
- `TENANT_MODEL = 'BTAPI.Client'` (line 111)

### 1.2  Show the schemas exist (1 min) — pane B

```bash
PGPASSWORD=password psql -h localhost -U admin -d btpostgres \
    -c "SELECT schema_name FROM information_schema.schemata WHERE schema_name IN ('public','se1','se2');"
```

> "Three real PostgreSQL schemas. `public` holds tenant metadata + the Django admin. `se1` and `se2` each hold one customer's defect data, fully isolated."

### 1.3  Show tenant routing by hostname (2 min) — pane B

**SE Tenant 1 user logs in to SE Tenant 1 — succeeds:**

```bash
curl -s -X POST http://se1.localhost:8000/api/token/ \
    -H "Content-Type: application/json" \
    -d '{"username":"user_1","password":"pw"}' | python3 -m json.tool
```

Expect HTTP 200 with `access` and `refresh` tokens.

**Same SE1 user tries SE Tenant 2 — fails:**

```bash
curl -s -X POST http://se2.localhost:8000/api/token/ \
    -H "Content-Type: application/json" \
    -d '{"username":"user_1","password":"pw"}'
```

Expect HTTP 401 — `user_1` does not exist in the `se2` schema at all.

> "Same URL path, same credentials, different subdomain — different schema, different user table. The middleware decides which schema to use based on the hostname, before authentication even runs."

### 1.4  Show data isolation on a real endpoint (2 min) — pane B

Capture each tenant's token into a shell variable:

```bash
SE1_TOKEN=$(curl -s -X POST http://se1.localhost:8000/api/token/ \
    -H "Content-Type: application/json" \
    -d '{"username":"user_1","password":"pw"}' | python3 -c "import json,sys; print(json.load(sys.stdin)['access'])")

SE2_TOKEN=$(curl -s -X POST http://se2.localhost:8000/api/token/ \
    -H "Content-Type: application/json" \
    -d '{"username":"user_6","password":"pw"}' | python3 -c "import json,sys; print(json.load(sys.stdin)['access'])")
```

List all defect reports per tenant:

```bash
curl -s -H "Authorization: Bearer $SE1_TOKEN" http://se1.localhost:8000/api/reports/ALL/ | python3 -m json.tool
curl -s -H "Authorization: Bearer $SE2_TOKEN" http://se2.localhost:8000/api/reports/ALL/ | python3 -m json.tool
```

> "SE Tenant 1 sees only its own `Dr1` (\"Unable to search\"). SE Tenant 2 sees only its own `Dr1` (\"Hit count incorrect\") — same primary key, different rows in different schemas. Neither tenant can see the other's data, even though both queries hit the same Django process and the same Postgres instance."

### 1.5  Honest limitations (30 s)

Acknowledge upfront, before they ask:

> "Two known limitations we'd address in a follow-on release: (1) the `BTAPI` app is dual-listed in shared and tenant app lists, which creates unused shadow tables in the public schema — isolation still works correctly via the router, but it's a cleanup we'd want to do. (2) Our automated test suite uses an in-memory SQLite config to run fast, so it doesn't exercise the tenants layer. We did the multi-tenant smoke test you just saw manually."

---

## 2. API documentation (≈ 4 min)

### 2.1  Frame (15 s)

> "Sprint 3 lecture material covered `drf-spectacular` for OpenAPI 3.0. We instrumented every endpoint so the schema is generated from the code itself — no separate doc to drift out of sync."

### 2.2  Swagger UI walkthrough (2 min) — browser tab 1

Open `http://se1.localhost:8000/api/schema/swagger-ui/`.

Point out, in order:
- The five tag groups in the left rail: **Authentication**, **Defect Reports**, **Comments**, **Products**, **Metrics**.
- The auto-generated request/response schemas under each endpoint.
- Custom summaries (e.g. *"Update report status, severity, priority, or duplicate parent"*).
- The five documented query parameters on `PATCH /api/update/{id}/`.

### 2.3  Try an endpoint live in Swagger (1.5 min) — browser

1. Click `POST /api/token/` → **Try it out** → body `{"username":"user_1","password":"pw"}` → **Execute**.
2. Copy the `access` token.
3. Click the **Authorize** button at the top → paste `Bearer <token>` → **Authorize**.
4. Open `GET /api/reports/{status}/` → **Try it out** → `status = ALL` → **Execute**. Show the JSON response.

> "Reviewers can authenticate and exercise every endpoint without leaving the browser."

### 2.4  ReDoc + Postman as alternatives (30 s) — browser tab 2

Switch to `http://se1.localhost:8000/api/schema/redoc/` — show the cleaner read-only layout suitable for printing or sharing with a non-technical stakeholder. Mention the Postman collection in `postman/collections/` for engineers who prefer that workflow.

---

## 3. Automated endpoint tests (≈ 4 min)

### 3.1  Frame (15 s)

> "Sprint 3 §38 asked for one representative test per endpoint method. We wrote ten happy-path tests — covering all eight production endpoints plus the two simplejwt token endpoints — and three additional cases that pin the `CLOSED` terminal-state union and Owner-only `severity`/`priority`/`dev` role gating."

### 3.2  Run the suite (1 min) — pane C

```bash
python3 manage.py test --settings=BTConfig.settings_test BTAPI -v 2
```

Expected tail:

```
Ran 19 tests in <X>s
OK
```

(19 = 13 endpoint smoke tests + 6 classifier tests.)

### 3.3  Walk the test inventory (2 min)

Open `BTAPI/tests.py` and scroll. Don't read every test — call out:

- `EndpointSmokeTests.setUpTestData` — one fixture: 3 users (Tester / Dev / Po), one Developer profile, one Product, one DefectReport in `New` state.
- The 10 happy-path tests, one per endpoint method, named by what they exercise: `test_post_token_…`, `test_post_token_refresh_…`, `test_post_new_report_…`, `test_get_reports_by_status_…`, `test_get_assigned_defects_…`, `test_get_full_report_…`, `test_patch_update_report_new_to_open`, `test_post_comment_…`, `test_post_new_product_…`, `test_get_developer_metric_…`.
- Three additional regression / role-gate tests: `test_get_reports_closed_returns_terminal_states` (pins `CLOSED` to the union of Cannot Reproduce/Duplicate/Rejected), `test_patch_severity_priority_dev_by_owner_applies` (positive Owner path on the gated mutations), `test_patch_severity_by_non_owner_is_ignored` (negative path — silent no-op).

### 3.4  Honest scope statement (45 s)

> "These are happy-path smoke tests, not exhaustive workflow tests. They prove the wiring — URL → view → serializer → 2xx response — for every endpoint, which is what the §38 rubric asked for. The deeper coverage requirement was scoped to the new metrics module, which is segment 4."

---

## 4. Developer effectiveness metric + coverage (≈ 4 min)

### 4.1  Frame (30 s)

Open `BTAPI/metrics.py` (9 lines):

> "Sprint 3 §22–§24 defined a three-bucket classifier: Insufficient data / Good / Fair / Poor, based on a developer's reopened-to-fixed ratio. We extracted it into a pure function — no Django, no DB — so it can be unit-tested in isolation and reused. Sprint 3 §25 then required full statement and full branch coverage of this module."

### 4.2  Show the function and its branches (45 s)

Walk the four return paths:
- `fixed_count < 20` → `"Insufficient data"`
- ratio `< 1/32` → `"Good"`
- ratio `< 1/8` → `"Fair"`
- otherwise → `"Poor"`

> "Three `if` branches, four return values, two boundary thresholds — six tests cover every statement and every branch direction."

### 4.3  Show the six tests (45 s)

Open `BTAPI/tests.py::ClassifierTests`. Point at:
- Cases 1 & 2: `(0,0)` and `(19,0)` — the *insufficient-data* branch.
- Case 3: `(20,0)` — the *Good* branch.
- Cases 4 & 5: `(32,1)` and `(32,3)` — the *Fair* branch, including the `1/32` boundary.
- Case 6: `(32,4)` — the *Poor* branch, at the `1/8` boundary.

### 4.4  Run coverage (1 min) — pane C

```bash
coverage run --rcfile=.coveragerc manage.py test --settings=BTConfig.settings_test BTAPI
coverage report -m --include='BTAPI/metrics.py'
```

Expected output ends with:

```
Name              Stmts   Miss Branch BrPart  Cover   Missing
-------------------------------------------------------------
BTAPI/metrics.py      ?      0      ?      0  100.0%
```

> "`Cover` 100%, `Missing` empty. Both statement and branch coverage. This is the §25 grading hook."

*(Optional)* For a visual artifact, run `coverage html` and open `htmlcov/BTAPI_metrics_py.html` — every line green.

### 4.5  Hit the live endpoint on user_7 (30 s) — pane B

```bash
curl -s -H "Authorization: Bearer $SE2_TOKEN" \
    http://se2.localhost:8000/api/metric/user_7/ | python3 -m json.tool
```

Expect:

```json
{"report": "Insufficient data"}
```

> "user_7's setup is fixedCount=8, reopenedCount=1. The classifier's
> first gate requires at least 20 fixes before any meaningful judgment
> is made — with only 8 fixes, the correct answer is *Insufficient
> data*. This proves the §22-24 implementation is honest about its own
> data requirements rather than producing a noisy verdict."

---

## 5. Wrap-up & Q&A (≈ 2 min)

### 5.1  Recap slide (verbal is fine)

> "Sprint 3, four sub-projects, all delivered on `dev`:
>
> 1. **Multi-tenant deployment** — three live tenants, schema-level isolation, hostname-based routing.
> 2. **API documentation** — five tag groups, every endpoint instrumented, browseable via Swagger and ReDoc.
> 3. **Automated tests** — nineteen tests passing under a fast SQLite test config.
> 4. **Effectiveness classifier** — extracted, unit-tested, 100% statement and branch coverage.
>
> Total: 30 commits on `dev` since the Sprint 2 tag."

### 5.2  Anticipated questions and pre-baked answers

| Likely question | Short answer |
|---|---|
| *Why one schema per tenant instead of a tenant_id column?* | Stronger isolation, simpler queries, lower blast radius if a query forgets the tenant filter. Trade-off is that schema migrations cost more at scale. |
| *Why don't the automated tests cover multi-tenancy?* | The test config uses in-memory SQLite for speed (full suite < 5s). Multi-tenancy was validated by the manual smoke test you saw in segment 1. A second test pass under real Postgres + tenants is out of scope for Release 2. |
| *Why only happy-path smoke tests?* | §38 asked for one representative test per endpoint method. Deeper workflow + edge-case coverage is out of scope for Release 2. |
| *Why is `BTAPI` listed in both SHARED_APPS and TENANT_APPS?* | Convenience during the Sprint 3 cutover — splitting `BTAPI` into a `BTTenants` app for `Client`/`Domain` plus a tenant-only `BTAPI` is a planned cleanup. |
| *Can we onboard a new tenant live?* | Yes — `Client.objects.create(schema_name='newco', name='NewCo')` followed by a `Domain.objects.create(...)` row. `auto_create_schema=True` runs `CREATE SCHEMA` and the per-tenant migrations on save. |

---

## 6. Recovery playbook — if something breaks mid-demo

| Symptom | Fast fix |
|---|---|
| `psql: connection refused` | Postgres isn't running. **Postgres.app:** click the elephant icon → **Start**. **Homebrew:** `brew services start postgresql@16`. |
| `se1.localhost` / `se2.localhost` not resolving | macOS resolves `*.localhost` automatically. If it fails, fall back to `127.0.0.1` and pass `Host: se1.localhost` header: `curl -H "Host: se1.localhost" http://127.0.0.1:8000/api/token/ …`. |
| Swagger UI shows "no endpoints" | Hard-refresh (⌘⇧R). If still empty, restart the dev server in pane A. |
| `migrate_schemas` errors after a model change | The schema is real — drop and re-bootstrap: `dropdb btpostgres && createdb -O admin btpostgres && python3 manage.py migrate_schemas --shared && python3 manage.py migrate_schemas && python3 manage.py bootstrap_tenants`. **Only do this if you have time** — otherwise skip the broken segment and move on. |
| Tests fail unexpectedly | Run `python3 manage.py test --settings=BTConfig.settings_test BTAPI.tests.ClassifierTests` first (always green, pure-function). If even that fails, check `pip install -r requirements.txt` and the active venv. |
| Coverage report shows < 100% | Re-run with `--rcfile=.coveragerc`. If it's still low, you're running the wrong settings module — coverage must be run via `manage.py test --settings=BTConfig.settings_test`. |
| Live demo simply won't cooperate | Pivot to: (a) the Postman collection, (b) screenshots of a successful run, (c) the test output as the proof of behavior. Never silently struggle — say "let me fall back to the recorded output" and move on. |

---

## 7. Post-demo cleanup

```bash
# In pane A: Ctrl-C to stop runserver
deactivate                                   # exit venv
```

The Postgres instance can stay up — it's harmless and avoids cold-start cost next time.

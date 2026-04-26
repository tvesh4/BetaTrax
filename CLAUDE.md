# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BetaTrax is a Django REST API for managing beta software defect reports (COMP3297 Group F project). Testers submit defect reports; product owners and developers manage them through a role-enforced status workflow.

## Setup & Commands

```bash
# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Database setup
python3 manage.py migrate
python3 manage.py loaddata groups.json   # creates User/Developer/Owner groups

# Create admin user
python3 manage.py createsuperuser

# Run development server
python3 manage.py runserver

# Run tests
python3 manage.py test BTAPI

# Run a single test
python3 manage.py test BTAPI.tests.TestClassName.test_method_name
```

## Architecture

**Two Django apps:**
- `BTConfig/` — Django project config (settings, root URLs, ASGI/WSGI)
- `BTAPI/` — All models, serializers, views, permissions, utils, and URL routes

**Request flow:** `BTConfig/urls.py` → `/api/` prefix → `BTAPI/urls.py` → `@api_view` functions in `views.py`

**Authentication:** JWT via `simplejwt`. Tokens are obtained at `POST /api/token/` and include custom claims: `username`, `is_owner`, `is_developer`. All endpoints (except token) require `IsAuthenticated`.

**Authorization:** `BTAPI/permissions.py` defines three permission classes — `IsUser`, `IsDeveloper`, `IsOwner` — which check Django group membership (`User`, `Developer`, `Owner`). Groups are loaded from `groups.json`; users are assigned to groups via Django Admin.

**API Endpoints:**
- `POST /api/token/` — Login, returns JWT access + refresh tokens
- `POST /api/token/refresh/` — Refresh access token
- `POST /api/defect/` — Submit new defect report (`IsUser`)
- `GET /api/reports/<status>/` — List reports by status; supports `NEW`, `OPEN`, `ASSIGNED`, `FIXED`, `RESOLVED`, `REOPENED`, `CLOSED`, `ALL`
- `GET /api/reports/assigned/dev=<id>/` — List ASSIGNED reports for a developer (`IsDeveloper | IsOwner`)
- `GET /api/defect/<id>/` — Full report details
- `PATCH /api/update/<id>/` — Update report status, severity, priority, or parent (duplicate link); role-enforced transitions
- `POST /api/comment/<id>/` — Post a comment on a report
- `POST /api/product/` — Register a new product (`IsDeveloper | IsOwner`)

**Defect status workflow (role-enforced):**
```
NEW → OPEN or CLOSED   (Owner only)
OPEN → ASSIGNED        (Developer)
ASSIGNED → FIXED       (Developer)
FIXED → RESOLVED       (Owner)
RESOLVED → REOPENED    (User/Tester)
REOPENED → OPEN        (Owner)
```
Marking a report as a duplicate (setting `parent`) automatically moves it to `CLOSED`.

**Key model relationships:**
- `Product` has FKs to `ProductOwner` (ownerId) and `Developer` (devId) — no separate Tester model
- `DefectReport` has FKs to `Product`, `ProductOwner` (unused evaluatedById removed), `Developer` (assignedToId), and a self-referential FK `parent` for duplicate linking (with `children` reverse relation)
- `Comment` has FK to `DefectReport` (CASCADE), ordered by `-createdAt`

**Email notifications:** `BTAPI/utils.py` provides four functions called from `views.py`:
- `send_status_update_email(report)` — notifies tester on any status change
- `send_po_update_email(report)` — notifies product owner on status change
- `send_duplicate_update_email(report, dup_report)` — notifies tester when report is linked as duplicate
- `send_children_update_email(report)` — notifies testers of child reports when parent is updated

Emails are written to the `email/` directory (file-based backend, not sent to real recipients).

**Serializers:**
- `DefectReportSerializer` — full report with nested `comments` and `children` (read-only), writable `parent`
- `ReportLiteSerializer` — `id`, `title`, `status` only; use for list endpoints
- `UserTokenObtainPairSerializer` — extends simplejwt, adds `username`/`is_owner`/`is_developer` claims

## Key Constraints

- User/Developer/Owner accounts are created by a superuser via Django Admin; self-registration is not supported
- BrowsableAPIRenderer is disabled; API returns JSON only
- Database is SQLite (`db.sqlite3`) — excluded from git
- Migrations folder is excluded from git (`.gitignore`)

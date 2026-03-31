# BetaTrax
Group F of COMP3297 2025-2026 Semester 2

## Setup & Installation
1. Create and activate virtual environment:
   `python3 -m venv venv`
   `source venv/bin/activate`
2. Install dependencies: `pip install -r requirements.txt`
3. Apply migrations: `python3 manage.py migrate`
4. Start the development server: `python3 manage.py runserver`

## Key Assumptions for Sprint 1 Executable
- This increment is configured for a single product. A default product must be created via the Django Admin interface before use. All submitted defect reports are associated with this product.
- Authentication for Product Owners and Developers is out of scope for this sprint. API endpoints assume requests come from an authorised source. User records for Product Owners and Developers must be created via the Django Admin interface before assignment.
- Django is configured to write emails to the `email/` directory in the project root (file-based backend). Emails are not sent to real recipients.

## Limitations / Functionality Not Working Correctly
1. **Status saved as lowercase** — `patch_update_report` stores the status value as lowercase (e.g. `"open"`) but the model's `Status` choices are uppercase (`"OPEN"`). This causes subsequent status-based filtering to return no results.
2. **`evaluatedById` not recorded** — when a Product Owner accepts a defect (NEW→OPEN), the `evaluatedById` field is never set, so the evaluating owner is not persisted.
3. **No endpoint to list OPEN defects** — developers have no way to discover OPEN reports to claim. `get_reports` only handles `New` and `Fixed`; requesting any other status (e.g. `OPEN`, `ASSIGNED`, `RESOLVED`) will cause a server error due to an unbound variable.
4. **No status transition validation** — the PATCH endpoint accepts any status string without verifying it follows the legal workflow (NEW→OPEN→ASSIGNED→FIXED→RESOLVED). Illegal transitions (e.g. NEW→FIXED) are silently accepted.
5. **No automated tests** — `tests.py` is empty; no test coverage exists for any endpoint.

## API Endpoints Implemented (Sprint 1)
- `POST /api/defect/` — Submit a new defect report (PBI-1)
- `GET /api/defects/{status}/` — List reports by status; currently supports `New`, `Open`, `Assigned`, `Fixed`, and `All` for listing all reports (PBI-2, PBI-5)
- `GET /api/defect/{report_id}/` — Full details of a specific report (PBI-2)
- `GET /api/defects/Assigned/dev={dev_id}/` — List all ASSIGNED defects for a specific developer (PBI-3)
- `PATCH /api/defect/{id}/{new_status}/` — Update report status and assigned developer; optional suffixes: `/dev={dev_id}/`, `/severity={Low, Minor Major, Critical}/` and/or `/priority={Low, Medium, High, Critical}/`. Status must be updated according to the basic flow (New > Open > Assigned > Fixed > Resolved) (PBI-2, PBI-3, PBI-4, PBI-5)

## Team Members & Contributions
- **Lam Chin Yui: Product Backlog, Partial Domain Model**
- **Lai Tsz Ng: Communications, UI Storyboards, Source Code**
- **Wang Yam Yuk: UI Storyboards, Source Code**
- **Kumar Tvesha Sanjay: Product Backlog, Partial Domain Model**

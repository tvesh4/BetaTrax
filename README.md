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

## Key Assumptions for Sprint 1 Executable
- This increment is configured for 1 product. A default product (e.g., with ID "PROD-1") must be created via the Django Admin interface before use. All submitted defect reports are associated with this product.
- Authentication for Product Owners and Developers is out of scope for this sprint. API endpoints assume the requests are from an authenticated source. User records for Product Owners and Developers must be created via the Django Admin interface to allow assignment.
- Django is configured to write emails to the console for easy testing as per technical note. Actually emails are not sent.

## Key Assumptions for Sprint 2 Increment
- **Multi-Product Support:** Unlike Sprint 1, the system now supports multiple products. Product Owners (POs) can register new products directly via the API.
- **Role-Based Workflow:** While user registration remains an Admin-only task, the API now enforces status transitions based on roles (e.g., only Developers can mark a bug as "Fixed"; only Testers can "Reopen").
- **Duplicate Logic:** Marking a report as a duplicate via the `parent_report` field automatically triggers a terminal "Closed" state to prevent redundant work.
- **Email Simulation:** Emails are still configured to output to the console/logs to verify PBI-1 and PBI-4 notification requirements without external SMTP setup.


## Limitations / Functionality Not Working Correctly
- **Circular Duplicates:** While the API prevents a report from duplicating itself, deep circular linking (A -> B -> A) is not yet blocked by the database constraints.
- **Self-Service Registration:** New Product Owners and Developers must still be created by a Superuser via `/admin` before they can be assigned to products or reports.

## API Endpoints Implemented 
- `POST /api/products/` - Register a new product. (PBI-5)
- `POST /api/comment/<str:id>/` - Post a new comment on a defect report. (PBI-6 in Sprint 1)
- `POST /api/defect/` - Submit a new defect report. (PBI-1)
- `GET /api/reports/<str:status>/` - List reports with support for status filtering (including NEW, OPEN, ASSIGNED, FIXED, RESOLVED, REOPENED, DUPLICATE, REJECTED,and CANNOT REPRODUCE). (PBI-10)
- `PATCH /api/update/<str:id>/` - Update report status, severity, priority, or link a parent duplicate. (PBI-6, 7, 8, 9)
- `GET /api/reports/assigned/<str:dev_id>/` - View all active tasks for a specific developer. (PBI-3)
- `GET /api/defect/<str:id>/` - View full detail of a specific defect report. 
- `POST /api/token/` - Get authentication token for a specific user with username and password. 
- `GET /api/metric/<str:id>` - Get effectiveness report of a specific developer. 

## Team Members & Contributions
- **Lam Chin Yui: Product Backlog, Partial Domain Model**
- **Lai Tsz Ng: Communications, UI Storyboards, Source Code**
- **Wang Yam Yuk: UI Storyboards, Source Code**
- **Kumar Tvesha Sanjay: Product Backlog, Partial Domain Model**

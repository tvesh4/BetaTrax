# BetaTrax
Group F of COMP3297 2025-2026 Semester 2

## Setup & Installation
1. Set up virtual environment: python3 -m venv venv
2. Install required pip packages in venv: pip install -r requirements.txt
3. Start django server: python3 manage.py runserver

## Key Assumptions for Sprint 1 Executable
- This increment is configured for 1 product. A default product (e.g., with ID "PROD-1") must be created via the Django Admin interface before use. All submitted defect reports are associated with this product.
- Authentication for Product Owners and Developers is out of scope for this sprint. API endpoints assume the requests are from an authenticated source. User records for Product Owners and Developers must be created via the Django Admin interface to allow assignment.
- Django is configured to write emails to the console for easy testing as per technical note. Actually emails are not sent.

## Limitations / Functionality Not Working Correctly
- 

## API Endpoints Implemented (Sprint 1)
- `POST /api/defects/` - Submit a new defect report. (PBI-1)

## Team Members & Contributions
- **Lam Chin Yui:**
- **Lai Tsz Ng:** 
- **Wang Yam Yuk:**
- **Kumar Tvesha Sanjay:** 

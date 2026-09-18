# Module 8 dashboard skeleton

This module is intentionally a local-only Streamlit shell for the SIH26161 dashboard. It is not a production deployment layer, not a real database client, and not a simulation engine.

## Scope
- Local-only user interface
- No authentication
- No cloud deployment
- No direct database access from the UI
- Requests go through the M0/API boundary only
- Mock responses are used until the backend is implemented

## Structure
- `app.py`: dashboard entry point
- `pages/1_Home.py`: overview landing page
- `pages/2_Add_Site.py`: mock site intake form
- `pages/3_Site_Dashboard.py`: scenario and impact dashboard shell
- `components/map.py`: map display helper
- `components/metrics.py`: metric card helper
- `components/site_form.py`: form builder for site onboarding and scenario resolution
- `services/api_client.py`: local mock API client that reads JSON fixtures under `data/mock/json/`

## Run locally
```bash
streamlit run modules/m8_dashboard/app.py
```

## Notes
- The UI communicates through mocked M0 responses only.
- No real solver, impact, or satellite logic is implemented here.
- This shell intentionally relies on the existing mock fixtures already present in the repo.

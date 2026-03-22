# Public Service CRM (PSCRM)

Centralized public grievance platform for end-to-end complaint submission, AI categorization, geo-routing, ticketing, and transparent resolution tracking.

## Monorepo Structure

- `frontend/`: React + Vite citizen-facing interface and analytics dashboard
- `backend/`: Flask API, AI bridge, ticketing and routing services
- `docs/`: Architecture and implementation notes

## Quick Start

### 1) Frontend

```bash
cd frontend
npm install
npm run dev
```

### 2) Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

Optional (for BERT/TensorFlow experiments):

```bash
pip install -r requirements-ml.txt
```

API runs on `http://localhost:5000` and frontend on `http://localhost:5173` by default.

### 3) Data Persistence (Configured)

Backend is now configured to use persistent SQL storage by default.

- Default DB URL: `sqlite:///pscrm.db` (file created in `backend/`)
- To switch to MySQL: set `MYSQL_URL` (for example `mysql+pymysql://user:password@localhost:3306/pscrm`)
- To force old ephemeral mode: set `USE_IN_MEMORY_REPO=true`

Windows PowerShell example:

```powershell
$env:MYSQL_URL = "sqlite:///pscrm.db"
$env:USE_IN_MEMORY_REPO = "false"
python run.py
```

## Core Features Implemented

- Dual-theme UI (Dark/Light) with WCAG-aware accent usage
- Authentication with role-based access (`citizen`, `officer`, `admin`, `mayor`)
- Live NLP complaint classifier demo
- Animated vertical resolution timeline
- Recharts-based analytics dashboard
- Ticket generation (`IM-YYYY-XXXXX`)
- Geo-routing to nearest ward/field officer
- Real-time status updates via polling endpoints
- **Admin Manager Dashboard** with interactive CRUD:
  - Officer Manager: Add/edit/delete officers, assign to departments
  - Department Manager: Create/manage service departments
  - Citizen Manager: View and manage registered citizens
- Mayor Analytics Dashboard: City-wide complaint analytics by type and status
- Architecture-ready hooks for mobile app, voice/IVR, and SMS intake

## Data Layer

- Structured entities (complaints, users, departments, logs): SQLAlchemy-backed repositories
- Default runtime uses persistent SQL file storage (`sqlite:///pscrm.db`)
- Optional MySQL support via `MYSQL_URL`
- Optional ephemeral mode via `USE_IN_MEMORY_REPO=true`

## AI Stack

- Current: TF-IDF + Naive Bayes classifier (`scikit-learn`)
- Planned: BERT/TensorFlow model upgrade path via model service interface

## Demo Credentials

- Officer: `officer.ward12@pscrm.gov` / value from `OFFICER_BOOTSTRAP_PASSWORD`
- Admin: `admin@pscrm.gov` / value from `ADMIN_BOOTSTRAP_PASSWORD`
- Mayor: `mayor@pscrm.gov` / value from `MAYOR_BOOTSTRAP_PASSWORD`
- Citizen: Use the in-app sign-up flow to create an account

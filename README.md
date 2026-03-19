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

## Core Features Implemented

- Dual-theme UI (Dark/Light) with WCAG-aware accent usage
- Authentication with role-based access (`citizen`, `officer`, `admin`)
- Live NLP complaint classifier demo
- Animated vertical resolution timeline
- Recharts-based analytics dashboard
- Ticket generation (`IM-YYYY-XXXXX`)
- Geo-routing to nearest ward/field officer
- Real-time status updates via polling endpoints
- Architecture-ready hooks for mobile app, voice/IVR, and SMS intake

## Data Layer

- Structured complaints: SQLAlchemy model intended for MySQL deployments
- Flexible media metadata + logs: MongoDB repository abstraction
- Dev mode uses in-memory repositories for fast startup

## AI Stack

- Current: TF-IDF + Naive Bayes classifier (`scikit-learn`)
- Planned: BERT/TensorFlow model upgrade path via model service interface

## Demo Credentials

- Officer: `officer.ward12@pscrm.gov` / value from `OFFICER_BOOTSTRAP_PASSWORD`
- Admin: `admin@pscrm.gov` / value from `ADMIN_BOOTSTRAP_PASSWORD`
- Citizen: Use the in-app sign-up flow to create an account

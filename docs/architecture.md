# PSCRM Architecture

## System Objective

PSCRM centralizes citizen grievances across municipal, state, and central governance layers while preserving transparency and automated routing.

## Key Components

1. Citizen Interface (React)
- Complaint registration and evidence-ready form
- Real-time NLP categorization demo
- Resolution timeline and analytics dashboard
- Live theme toggle with accessibility-first contrast choices

2. API and Workflow Layer (Flask)
- `/api/complaints` for ticket creation
- `/api/classify` for NLP service
- `/api/complaints/<ticket>/timeline` for progress tracking
- `/api/analytics` for dashboard aggregates

3. Intelligence Layer
- Current classifier: TF-IDF + Naive Bayes (scikit-learn)
- Planned upgrade path: BERT/TensorFlow model via service abstraction
- Geo-routing module assigning nearest ward and field officer

4. Data Layer (Hybrid)
- Structured records: MySQL via SQLAlchemy repository
- Media metadata and logs: MongoDB repository
- In-memory fallback for local development and demos

## Multi-Channel Intake Strategy

Active channels:
- Web portal
- Mobile app (API-ready)

Planned channels:
- Voice/IVR gateway
- SMS ingestion gateway

All channels map to a single normalized complaint payload before ticketing.

## Ticket Lifecycle

1. Complaint Registered
2. AI Categorization
3. Geo Routing
4. Field Action
5. Issue Resolved

Tickets follow `IM-YYYY-XXXXX` for traceability and audit readiness.

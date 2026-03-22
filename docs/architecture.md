# PSCRM Architecture — National Public Grievance Grid

## System Objective

PSCRM centralizes citizen grievances across **Local (ULB)**, **State**, and **Central** governance layers while preserving transparency, automated routing, and cross-tier accountability.

## Governance Tiers

All tickets carry `origin_tier` and `current_tier` fields using the `GovernanceTier` enum:
- **Local** — Municipal Corporation / ULB / Panchayat
- **State** — State PWD, State Health Dept, etc.
- **Central** — Central Ministry (MoHUA, MoRTH, etc.)

## Universal Ticket ID

Format: `IM-YYYY-STATE-CITY-HEX` (e.g., `IM-2026-MH-MUM-3A7F`)

## Key Components

1. **Citizen Interface** (React + Vite)
   - Complaint registration, NLP categorization demo, resolution timeline, analytics dashboard

2. **API and Workflow Layer** (Flask)
   - Core lifecycle: `/api/complaints`, `/api/classify`, `/api/complaints/<ticket>/timeline`
   - Tier transfer: `/api/complaints/<ticket>/transfer`, `/api/complaints/<ticket>/audit`
   - Ownership: `/api/complaints/<ticket>/ownership`
   - Search: `/api/search`, `/api/search/by-tier`
   - Admin: `/api/admin/registry`, `/api/admin/jurisdictions`
   - Analytics: `/api/analytics`, `/api/dashboard/*`

3. **Service Registry** (`service_registry.py`)
   - Maps region keys (e.g., `MH-MUM`) to lazily-connected SQL databases
   - Bootstrapped from JSON config or auto-registers `IN-DEV` for development

4. **Intelligence Layer**
   - Current: TF-IDF + Naive Bayes (scikit-learn)
   - Planned: BERT/TensorFlow upgrade via service abstraction
   - Geo-routing with state/city codes and governance tier detection

5. **Data Layer** (Hybrid)
   - Structured records: SQLAlchemy (SQLite/MySQL) per-region via Service Registry
   - Global Index: MongoDB or in-memory for cross-region search
   - Jurisdiction Layers: GeoJSON polygons for overlapping authority resolution

6. **Audit & Accountability**
   - `TierTransferAudit` records with SHA-256 checksums for tamper detection
   - `OwnershipStake` model with rules: single primary, single SLA owner, shares ≤ 1.0

## Ticket Lifecycle

1. Complaint Registered (with `origin_tier`)
2. AI Categorization
3. Geo Routing (ward + regional codes)
4. Field Action
5. Tier Transfer / Escalation (optional, creates audit trail)
6. Issue Resolved

## Multi-Channel Intake

Active: Web, Mobile (API-ready) · Planned: Voice/IVR, SMS

## Detailed Schema

See [national_grievance_grid_schema.md](./national_grievance_grid_schema.md) for the full design document.

# CivicWeave — AI-Based Civic Grievance Intelligence System

**Tagline:** From Complaints to Civic Intelligence.

CivicWeave is an AI-assisted civic grievance management platform that helps citizens report local civic problems and helps municipal authorities identify, understand, prioritize, and resolve them efficiently.

> **Note:** All seeded data is fictional development data for demonstration purposes.

## Features

- **Smart Complaint Analysis** — Rule-based NLP classification with department mapping
- **Incident Intelligence** — Semantic similarity + spatial + temporal verification
- **Explainable Prioritization** — Transparent rule-based priority estimation
- **Role-based Dashboards** — Citizen, Department Officer, and Super Admin
- **Interactive Maps** — Leaflet/OpenStreetMap for location selection and nearby incidents
- **Complete Lifecycle** — Submit → Analyze → Link → Prioritize → Resolve → Feedback

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| Frontend | React, Vite, Tailwind CSS, React Router, Axios, Recharts, Leaflet |
| Backend | Python, FastAPI, SQLAlchemy, Pydantic, JWT |
| Database | PostgreSQL with PostGIS |
| AI/ML | Sentence Transformers (all-MiniLM-L6-v2), scikit-learn, NumPy |

## Prerequisites

- Node.js 18+
- Python 3.11+
- Docker Desktop (for PostgreSQL/PostGIS)

## Quick Start

### 1. Start Database

```bash
docker compose up -d
```

### 2. Backend Setup

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
copy ..\.env.example ..\.env   # Windows
# cp ../.env.example ../.env   # macOS/Linux
```

### 3. Seed Demo Data

```bash
python -m scripts.seed_data --reset
```

This creates 30 citizens, 3 officers, 1 admin, 5 departments, 60+ complaints, and incident groups including the ABC Chowk road damage scenario.

### 4. Run Backend

```bash
uvicorn app.main:app --reload --port 8000
```

### 5. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

The maps use Leaflet with OpenStreetMap tiles. Tile attribution is shown on each map; no map API key is required.

## Demo Accounts

| Role | Email | Password |
|------|-------|----------|
| Super Admin | admin@civicweave.demo | admin123 |
| Road Officer | officer.roads@civicweave.demo | officer123 |
| Water Officer | officer.water@civicweave.demo | officer123 |
| Citizen | citizen01@demo.local | citizen123 |

## End-to-End Demo Scenario

1. Log in as `citizen01@demo.local`
2. Go to **Report Issue**
3. Enter: *"There is a dangerous pothole near ABC Chowk"*
4. Select location near **18.5310, 73.8446** on the map
5. Run AI Analysis — the system should suggest the existing **Road Damage Near ABC Chowk** incident
6. Choose to link or submit separately
7. Log in as `officer.roads@civicweave.demo` to review the incident, confirm links, and manage priority/status

## Running Tests

```bash
cd backend
pytest tests/ -v
```

## AI Linking Evaluation

```bash
cd backend
python -m scripts.evaluate_linking
```

Compares semantic-only, semantic+spatial, and full (semantic+spatial+temporal) linking strategies on labeled demo pairs.

## Project Structure

```
civicweave/
├── frontend/          # React + Vite application
├── backend/
│   ├── app/
│   │   ├── ai/        # Classification, embeddings, linking, priority
│   │   ├── models/    # SQLAlchemy models
│   │   ├── routers/   # API endpoints
│   │   ├── services/  # Business logic
│   │   └── security/  # JWT authentication
│   ├── scripts/       # Seed data, evaluation
│   └── tests/         # Pytest test suite
├── docker-compose.yml
└── .env.example
```

## Environment Variables

See `.env.example` for all configuration options including:

- `DATABASE_URL` — PostgreSQL connection string
- `SECRET_KEY` — JWT signing key
- `CLOUDINARY_*` — Optional image upload (works without Cloudinary)
- `SEMANTIC_WEIGHT`, `SPATIAL_WEIGHT`, `TEMPORAL_WEIGHT` — Linking engine weights
- `DEFAULT_SPATIAL_RADIUS_METERS`, `DEFAULT_TEMPORAL_WINDOW_DAYS` — Verification thresholds

## API Documentation

With the backend running, visit:

- Swagger UI: http://localhost:8000/docs
- Health check: http://localhost:8000/api/health

## License

Development/educational project.

# DBD Survivor Build Creator

A full-stack Dead by Daylight survivor build generator with AI-powered recommendations, real-time perk data from Nightlight.gg, and weekly Shrine of Secrets tracking.

## Features

- **Theme-based build generation** — Describe a playstyle, get a meta build
- **Category builder** — Mix perks from specific categories (stealth, healing, chase, etc.)
- **Weighted perk graph** — Perk co-occurrence graph built from Nightlight.gg top builds
- **Shrine of Secrets** — Weekly shrine scraping so you know what's purchasable
- **Owned survivor filter** — Only show perks you own
- **AI explanations** — Strategy breakdown for every build

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React + TypeScript + Tailwind CSS |
| Backend | FastAPI (Python) |
| Database | PostgreSQL + pgvector |
| Cache | Redis |
| Scraping | Playwright |
| Scheduler | APScheduler |
| AI | Claude API (claude-sonnet-4-20250514) |
| Graph | NetworkX |
| Deployment | Docker Compose |

## Quick Start

### Prerequisites
- Docker + Docker Compose
- Node.js 18+
- Python 3.11+

### 1. Clone and configure
```bash
git clone <repo>
cd dbd-build-creator
cp .env.example .env
# Edit .env with your values
```

### 2. Load perk data
```bash
# Place your perks CSV at scripts/perks.csv
# Format: name,description,owner (owner = survivor name or "base")
docker compose run --rm backend python -m app.workers.perk_loader
```

### 3. Start everything
```bash
docker compose up --build
```

Frontend: http://localhost:5173  
Backend API: http://localhost:8000  
API Docs: http://localhost:8000/docs

## CSV Format

```csv
name,description,owner
Adrenaline,"You've been through a lot, but when the exit gates are powered, you get a burst of speed and healing.",Meg Thomas
Dead Hard,"For one brief moment you become intangible, dodging damage.",David King
...
```

## Project Structure

```
dbd-build-creator/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI route handlers
│   │   ├── core/         # Config, AI client, graph engine
│   │   ├── db/           # Database connection + migrations
│   │   ├── models/       # SQLAlchemy ORM models
│   │   ├── schemas/      # Pydantic request/response schemas
│   │   ├── services/     # Business logic
│   │   └── workers/      # Scraper + perk loader
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── hooks/        # Custom hooks
│   │   ├── pages/        # Page components
│   │   ├── store/        # Zustand state
│   │   └── types/        # TypeScript types
│   ├── Dockerfile
│   └── package.json
├── docker/
│   └── init.sql          # DB initialization
├── docker-compose.yml
└── .env.example
```
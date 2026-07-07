# FPVBattle Stats

FPVBattle Stats is a monorepo for three independent applications:

- `scraper`: synchronizes historical and current FPVBattle race results into a relational database
- `backend`: serves analytical APIs for scoreboards, pilot trends, country summaries, and streaks
- `frontend`: React + Vite client for daily standings and historical analytics

## Stack

- Python 3.12 for the scraper and backend
- FastAPI for the API layer
- SQLAlchemy 2 with repository and unit-of-work patterns
- SQLite for local development and PostgreSQL-ready SQLAlchemy configuration for Railway
- React 18, Vite, and Recharts for visualization

## Repository Layout

```text
backend/              FastAPI application
scraper/              scraping CLI and sync workflows
frontend/             React + Vite client
shared/python/        shared domain models, repositories, and DB wiring
docs/                 product and architecture documentation
```

## Local Setup

1. Create a Python virtual environment.
2. Install dependencies from `requirements.txt`.
3. For the frontend, run `npm install` inside `frontend/`.
4. Copy `.env.example` to `.env` if you want custom local settings.

## Run

Backend:

```bash
uvicorn backend.app.main:app --reload
```

Scraper:

```bash
python -m scraper.app.cli.main sync-historical
python -m scraper.app.cli.main sync-current
python -m scraper.app.cli.main sync-day 2026-07-02 --class open
```

Frontend:

```bash
cd frontend
npm run dev
```

## Notes

- The scraper always trusts points and categories displayed on the website.
- Historical days are treated as immutable after ingestion.
- Schema changes are made by editing SQLAlchemy models directly; Alembic is intentionally not used.

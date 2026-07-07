# AGENTS.md

## Project Overview

FPVBattle Stats is a showcase analytics platform for FPVBattle race history. It ingests daily results from `ua-velocidrone.fun`, stores them in a relational database, exposes analytical APIs, and renders historical performance views in a React frontend.

The monorepo contains three independent applications:

- `scraper`: fetches open and whoop class results, backfills history, and syncs the active UTC race day
- `backend`: FastAPI service that exposes scoreboards and analytics.
- `frontend`: React + Vite client for daily views and pilot analytics.

## Architecture

- Python shared core in `shared/python/fpvbattle_core` holds SQLAlchemy models, repositories, and the unit-of-work implementation.
- The scraper is CLI-driven and writes data through the shared repositories.
- The backend is read-oriented and builds analytical responses from SQLAlchemy queries.
- The frontend consumes the backend only; it does not read the database directly.
- The database layer must remain portable between SQLite for local development and PostgreSQL for Railway deployment.

## Folder Structure

```text
backend/
  app/
    api/
    core/
    db/
    schemas/
    services/
scraper/
  app/
    cli/
    core/
    parsers/
    services/
frontend/
  src/
    api/
    components/
    context/
    hooks/
    pages/
    styles/
shared/
  python/
    fpvbattle_core/
docs/
```

## Naming Conventions

- Use `snake_case` for Python modules, functions, and variables.
- Use `PascalCase` for React components, Python classes, and Pydantic schemas.
- Use `race_class` instead of bare `class` in Python and database code.
- Database model classes end with `Model`.
- Repository classes end with `Repository`.
- Services that coordinate workflows end with `Service`.

## Coding Standards

- Keep business rules explicit; do not infer scoring when the source site already displays points.
- Prefer typed functions and typed API schemas.
- Keep comments short and only where they reduce ambiguity.
- Avoid hidden side effects across layers; scraper parsing, persistence, API querying, and UI rendering should stay separated.
- Preserve ASCII unless a file already justifies Unicode usage.

## Database Rules

- `day_spec` is unique on `(date, race_class)`.
- `pilots` is unique on `(pilot)`.
- `results` is unique on `(day_spec_ref, pilot_ref)`.
- `season_leaderboard` is unique on `(day_spec_ref, pilot_ref)`.
- All scraper writes must be idempotent. Re-running syncs must never create duplicate logical rows.
- When a day is re-synced, replace that day’s results and season leaderboard rows inside one unit of work.
- Historical open-class rows that predate categories must store `category = null`.

## Scraping Workflow

- Historical start date: `2023-11-15`.
- On first launch, backfill all days from the historical start date to the selected end date.
- Historical sync should skip or safely overwrite by unique key without creating duplicates.
- Current-day sync should run on a 30-minute cadence at `00:05`, `00:35`, `01:05`, and so on.
- Because the site finalizes a day around `00:10 UTC` of the next day, the scraper should treat `00:00-00:09 UTC` as the previous active results window.
- Open class may contain `Gold`, `Silver`, `Bronze`, and `Unranked` categories. Older open days may have no categories.
- Whoop class has no categories and should store `category = null`.
- Always trust track, quad-of-the-day, points, and leaderboard values as displayed by the source site.

## Deployment Notes

- Railway target stack: FastAPI backend, Python scraper worker/cron, React frontend static build.
- Keep configuration environment-driven through `.env` and Railway variables.
- Local development uses SQLite; production should switch to PostgreSQL by updating `FPVBATTLE_DATABASE_URL`.
- Do not introduce Alembic during this development phase. Update SQLAlchemy models directly while the schema is still fluid.

## Roadmap

- Harden the HTML parser against the exact source markup once real pages are sampled and tested.
- Add scheduler entrypoints for Railway cron execution.
- Add richer backend endpoints for hover-card consistency stats and logarithmic pilot comparison views.
- Add frontend controls for date selection, season selection, and chart series toggles.
- Add automated tests with HTML fixtures captured from the source site.
- Add PostgreSQL verification before deployment.

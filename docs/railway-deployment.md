# Railway Deployment

This repository deploys cleanly to Railway as four services:

- `PostgreSQL`
- `backend`
- `scraper`
- `frontend`

## Prerequisites

- Push this repository to GitHub.
- Create one Railway project.
- Add a PostgreSQL service inside that project.

## Python Packaging

`requirements.txt` now installs the shared package from `shared/python`, so both the backend and scraper can import `fpvbattle_core` without setting `PYTHONPATH`.

## Backend Service

- Service source: this repository root
- Install command:

```bash
pip install -r requirements.txt
```

- Start command:

```bash
bash railway/backend-start.sh
```

- Variables:

```text
FPVBATTLE_DATABASE_URL=${{Postgres.DATABASE_URL}}
FPVBATTLE_CORS_ORIGINS=["https://your-frontend-domain"]
```

## Scraper Service

- Service source: this repository root
- Install command:

```bash
pip install -r requirements.txt
```

- Start command:

```bash
bash railway/scraper-sync-current.sh
```

- Variables:

```text
FPVBATTLE_DATABASE_URL=${{Postgres.DATABASE_URL}}
```

- Cron schedule:

```text
5,35 * * * *
```

## Frontend Service

- Service source: `frontend/`
- Install command:

```bash
npm ci
```

- Build command:

```bash
npm run build
```

- Start command:

```bash
npm run start
```

- Variables:

```text
VITE_API_BASE_URL=https://your-backend-domain/api
```

## Copy SQLite Into Railway PostgreSQL

If you want to migrate your current local SQLite database instead of rebuilding history, run:

```bash
python scripts/copy_sqlite_to_postgres.py ^
  --source sqlite:///data/fpvbattle.db ^
  --target "postgresql+psycopg://USER:PASSWORD@HOST:PORT/railway" ^
  --truncate-target ^
  --yes
```

Use the Railway PostgreSQL connection string for `--target`. Only use `--truncate-target` when you intentionally want to replace all FPVBattle tables in Postgres.

## Safer Alternative

If your source data can be regenerated from `ua-velocidrone.fun`, the safer production bootstrap is:

1. Deploy PostgreSQL and backend.
2. Point scraper env at PostgreSQL.
3. Run `python -m scraper.app.cli.main sync-historical`.
4. Enable the cron scraper afterward.

You can also use the helper script during bootstrap:

```bash
bash railway/scraper-sync-historical.sh
```

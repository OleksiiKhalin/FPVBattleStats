#!/usr/bin/env bash
set -euo pipefail

exec python -m scraper.app.cli.main sync-current

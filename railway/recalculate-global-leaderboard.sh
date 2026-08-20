#!/usr/bin/env bash
set -euo pipefail

exec python -m scraper.app.cli.main recalculate-global-leaderboard --class all

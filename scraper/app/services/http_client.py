from __future__ import annotations

import logging
import random
import time

import httpx


class BattleHttpClient:
    def __init__(
        self,
        *,
        timeout_seconds: float,
        request_delay_seconds: float,
        request_jitter_seconds: float,
        request_max_retries: int,
        request_backoff_seconds: float,
    ) -> None:
        self._client = httpx.Client(
            timeout=timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": "fpvbattle-stats-scraper/0.1"},
        )
        self._logger = logging.getLogger(__name__)
        self._request_delay_seconds = request_delay_seconds
        self._request_jitter_seconds = request_jitter_seconds
        self._request_max_retries = request_max_retries
        self._request_backoff_seconds = request_backoff_seconds
        self._last_request_started_at = 0.0

    def fetch(self, url: str) -> httpx.Response:
        last_error: Exception | None = None
        for attempt in range(1, self._request_max_retries + 1):
            self._wait_for_rate_limit()
            self._logger.info("Fetching %s (attempt %s/%s)", url, attempt, self._request_max_retries)
            self._last_request_started_at = time.monotonic()
            try:
                response = self._client.get(url)
                response.raise_for_status()
                self._logger.info(
                    "Fetched %s with status=%s content_type=%s",
                    url,
                    response.status_code,
                    response.headers.get("content-type", "unknown"),
                )
                return response
            except Exception as exc:
                last_error = exc
                self._logger.warning("Fetch failed for %s: %s", url, exc)
                if attempt < self._request_max_retries:
                    sleep_seconds = self._request_backoff_seconds * attempt
                    self._logger.info("Backing off for %.2fs before retrying %s", sleep_seconds, url)
                    time.sleep(sleep_seconds)

        assert last_error is not None
        raise last_error

    def fetch_html(self, url: str) -> str:
        return self.fetch(url).text

    def _wait_for_rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_request_started_at
        target_delay = self._request_delay_seconds + random.uniform(0, self._request_jitter_seconds)
        remaining = target_delay - elapsed
        if remaining > 0:
            self._logger.debug("Sleeping %.2fs to respect scraper rate limits", remaining)
            time.sleep(remaining)

    def close(self) -> None:
        self._client.close()

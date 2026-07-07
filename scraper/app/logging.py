from __future__ import annotations

import logging
import sys
from pathlib import Path


class _LevelRangeFilter(logging.Filter):
    def __init__(self, *, min_level: int, max_level: int | None = None) -> None:
        super().__init__()
        self._min_level = min_level
        self._max_level = max_level

    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelno < self._min_level:
            return False
        if self._max_level is not None and record.levelno > self._max_level:
            return False
        return True


def configure_logging(level: int = logging.INFO, *, log_dir: Path | None = None) -> None:
    target_log_dir = log_dir or (Path(__file__).resolve().parents[2] / "data" / "logs")
    target_log_dir.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()

    console_info_handler = logging.StreamHandler(sys.stdout)
    console_info_handler.setLevel(level)
    console_info_handler.addFilter(_LevelRangeFilter(min_level=level, max_level=logging.INFO))
    console_info_handler.setFormatter(formatter)

    console_warning_handler = logging.StreamHandler(sys.stderr)
    console_warning_handler.setLevel(max(level, logging.WARNING))
    console_warning_handler.addFilter(_LevelRangeFilter(min_level=max(level, logging.WARNING)))
    console_warning_handler.setFormatter(formatter)

    info_file_handler = logging.FileHandler(target_log_dir / "info.log", encoding="utf-8")
    info_file_handler.setLevel(level)
    info_file_handler.addFilter(_LevelRangeFilter(min_level=level, max_level=logging.INFO))
    info_file_handler.setFormatter(formatter)

    warning_file_handler = logging.FileHandler(target_log_dir / "warning.log", encoding="utf-8")
    warning_file_handler.setLevel(max(level, logging.WARNING))
    warning_file_handler.addFilter(_LevelRangeFilter(min_level=max(level, logging.WARNING), max_level=logging.WARNING))
    warning_file_handler.setFormatter(formatter)

    error_file_handler = logging.FileHandler(target_log_dir / "error.log", encoding="utf-8")
    error_file_handler.setLevel(max(level, logging.ERROR))
    error_file_handler.addFilter(_LevelRangeFilter(min_level=max(level, logging.ERROR)))
    error_file_handler.setFormatter(formatter)

    root_logger.addHandler(console_info_handler)
    root_logger.addHandler(console_warning_handler)
    root_logger.addHandler(info_file_handler)
    root_logger.addHandler(warning_file_handler)
    root_logger.addHandler(error_file_handler)

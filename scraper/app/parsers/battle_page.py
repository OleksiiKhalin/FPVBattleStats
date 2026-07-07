from __future__ import annotations

import json
import re
from datetime import date
from typing import Any

from bs4 import BeautifulSoup

from ..domain import ParsedDayPayload, ParsedResultRow, ParsedSeasonRow

NUMBER_PATTERN = re.compile(r"-?\d+(?:[.,]\d+)?")
CATEGORY_NAMES = {"gold", "silver", "bronze", "unranked"}


def parse_battle_page(*, html: str, target_date: date, race_class: str) -> ParsedDayPayload:
    dashboard_payload = _extract_dashboard_payload_from_json_blob(html)
    if dashboard_payload is not None:
        return _parse_dashboard_payload(
            dashboard_payload=dashboard_payload,
            target_date=target_date,
            race_class=race_class,
            source="json-blob",
        )

    soup = BeautifulSoup(html, "html.parser")
    embedded_dashboard_payload = _extract_dashboard_payload_from_scripts(soup)
    if embedded_dashboard_payload is not None:
        return _parse_dashboard_payload(
            dashboard_payload=embedded_dashboard_payload,
            target_date=target_date,
            race_class=race_class,
            source="script-json",
        )

    section_results = _extract_results_from_leaderboard_sections(soup)
    section_season_rows = _extract_season_rows_from_leaderboard_sections(soup)

    track = _extract_track(soup)
    quad_of_the_day = _extract_quad_of_the_day(soup)
    season = _extract_season(soup, target_date)
    results = section_results or _extract_results(soup)
    season_leaderboard = section_season_rows or _extract_season_leaderboard(soup)

    return ParsedDayPayload(
        date=target_date,
        race_class=race_class,
        season=season,
        track=track,
        quad_of_the_day=quad_of_the_day,
        results=results,
        season_leaderboard=season_leaderboard,
        source="html",
    )


def parse_dashboard_json(*, payload: dict[str, Any], target_date: date, race_class: str) -> ParsedDayPayload:
    return _parse_dashboard_payload(
        dashboard_payload=payload,
        target_date=target_date,
        race_class=race_class,
        source="api-json",
    )


def _extract_track(soup: BeautifulSoup) -> str:
    for selector in ("h1", "h2", ".track-title", ".track-name", ".page-title"):
        node = soup.select_one(selector)
        if node and node.get_text(strip=True):
            return node.get_text(" ", strip=True)
    return "Unknown track"


def _extract_quad_of_the_day(soup: BeautifulSoup) -> str | None:
    text = soup.get_text("\n", strip=True)
    match = re.search(r"(?:Drone|Quad) of the Day[:\s]+([^\n]+)", text, flags=re.IGNORECASE)
    return match.group(1).strip() if match else None


def _extract_season(soup: BeautifulSoup, target_date: date) -> str:
    text = soup.get_text("\n", strip=True)
    match = re.search(r"Season[:\s]+([^\n]+)", text, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return target_date.strftime("%Y-%m")


def _extract_results(soup: BeautifulSoup) -> list[ParsedResultRow]:
    rows: list[ParsedResultRow] = []
    current_category: str | None = None
    mode = "results"

    for node in soup.find_all(["h1", "h2", "h3", "h4", "table"]):
        if node.name != "table":
            heading = node.get_text(" ", strip=True).lower()
            if heading in {"gold", "silver", "bronze", "unranked"}:
                current_category = heading
            if "season" in heading and "leaderboard" in heading:
                mode = "season"
            continue

        extracted = _extract_table_rows(node, current_category, season_mode=False)
        if mode == "results":
            rows.extend(extracted)
    if rows:
        return _deduplicate_result_rows(rows)
    return _extract_results_from_list_items(soup)
    return rows


def _extract_season_leaderboard(soup: BeautifulSoup) -> list[ParsedSeasonRow]:
    rows: list[ParsedSeasonRow] = []
    current_category: str | None = None
    mode = "results"

    for node in soup.find_all(["h1", "h2", "h3", "h4", "table"]):
        if node.name != "table":
            heading = node.get_text(" ", strip=True).lower()
            if heading in {"gold", "silver", "bronze", "unranked"}:
                current_category = heading
            if "season" in heading and "leaderboard" in heading:
                mode = "season"
            continue

        if mode != "season":
            continue
        extracted = _extract_table_rows(node, current_category, season_mode=True)
        if extracted:
            rows.extend(
                ParsedSeasonRow(
                    pilot=row.pilot,
                    country=row.country,
                    category=row.category,
                    points=row.points,
                    place=row.place,
                )
                for row in extracted
            )
    if rows:
        return _deduplicate_season_rows(rows)
    return _extract_season_rows_from_list_items(soup)
    return rows


def _extract_table_rows(table, category: str | None, season_mode: bool) -> list[ParsedResultRow]:
    rows: list[ParsedResultRow] = []
    header_map = _extract_header_map(table)
    for tr in table.find_all("tr"):
        columns = [cell.get_text(" ", strip=True) for cell in tr.find_all(["td", "th"])]
        if not columns or _looks_like_header(columns):
            continue

        place = _value_as_int(_column_value(columns, header_map, {"place", "rank", "#"}), fallback=columns[0] if columns else None)
        pilot = _extract_pilot(columns, header_map)
        if not pilot:
            continue

        country = _extract_country(columns, header_map)
        points = _value_as_int(_column_value(columns, header_map, {"points", "pts"}), fallback=columns[-1] if columns else None)

        if season_mode:
            rows.append(
                ParsedResultRow(
                    pilot=pilot,
                    country=country,
                    category=category,
                    quad=None,
                    time=None,
                    points=points,
                    place=place,
                ),
            )
            continue

        quad = _extract_quad(columns, header_map)
        time_value = _extract_time(columns, header_map)
        rows.append(
            ParsedResultRow(
                pilot=pilot,
                country=country,
                category=category,
                quad=quad,
                time=time_value,
                points=points,
                place=place,
            ),
        )
    return rows


def _extract_header_map(table) -> dict[str, int]:
    for tr in table.find_all("tr"):
        header_cells = tr.find_all("th")
        if not header_cells:
            continue
        headers = [cell.get_text(" ", strip=True).lower() for cell in header_cells]
        mapping: dict[str, int] = {}
        for index, header in enumerate(headers):
            if header:
                mapping[header] = index
        if mapping:
            return mapping
    return {}


def _looks_like_header(columns: list[str]) -> bool:
    header_text = " ".join(columns).lower()
    return any(token in header_text for token in ("pilot", "place", "points", "time"))


def _extract_pilot(columns: list[str], header_map: dict[str, int] | None = None) -> str | None:
    candidate = _column_value(columns, header_map or {}, {"pilot", "player", "player name", "name"})
    if candidate and not _looks_numeric(candidate):
        return candidate.strip()
    for value in columns[1:]:
        if value and not _looks_numeric(value):
            return value.strip()
    return None


def _extract_country(columns: list[str], header_map: dict[str, int] | None = None) -> str | None:
    candidate = _column_value(columns, header_map or {}, {"country", "flag"})
    if candidate:
        normalized = candidate.strip().upper()
        if len(normalized) in {2, 3} and normalized.isalpha():
            return normalized
    for value in columns:
        if len(value) in {2, 3} and value.isalpha() and value.upper() == value:
            return value
    return None


def _extract_quad(columns: list[str], header_map: dict[str, int] | None = None) -> str | None:
    candidate = _column_value(columns, header_map or {}, {"quad", "model", "model name", "drone"})
    if candidate and not _looks_numeric(candidate):
        return candidate.strip()
    for value in columns[2:]:
        if value and ":" not in value and not value.isdigit() and value.lower() not in CATEGORY_NAMES:
            if _parse_float(value) is None:
                return value
    return None


def _extract_time(columns: list[str], header_map: dict[str, int] | None = None) -> float | None:
    candidate = _column_value(columns, header_map or {}, {"time", "track time", "lap time"})
    if candidate:
        parsed = _parse_float(candidate)
        if parsed is not None:
            return parsed
    for value in columns:
        if ":" in value or "." in value:
            number = _parse_float(value)
            if number is not None and number > 1:
                return number
    return None


def _parse_last_int(columns: list[str]) -> int | None:
    for value in reversed(columns):
        parsed = _parse_int(value)
        if parsed is not None:
            return parsed
    return None


def _parse_int(value: str) -> int | None:
    match = NUMBER_PATTERN.search(value.replace(",", "."))
    if not match:
        return None
    try:
        return int(float(match.group(0)))
    except ValueError:
        return None


def _parse_float(value: str) -> float | None:
    match = NUMBER_PATTERN.search(value.replace(",", "."))
    if not match:
        return None
    try:
        return round(float(match.group(0)), 3)
    except ValueError:
        return None


def _value_as_int(primary: str | None, fallback: str | None = None) -> int | None:
    if primary is not None:
        parsed = _parse_int(primary)
        if parsed is not None:
            return parsed
    if fallback is not None:
        return _parse_int(fallback)
    return None


def _column_value(columns: list[str], header_map: dict[str, int], names: set[str]) -> str | None:
    for header, index in header_map.items():
        if header in names or any(name in header for name in names):
            if index < len(columns):
                return columns[index]
    return None


def _looks_numeric(value: str) -> bool:
    return NUMBER_PATTERN.fullmatch(value.replace(":", "").replace(".", "").replace(",", "")) is not None


def _extract_results_from_list_items(soup: BeautifulSoup) -> list[ParsedResultRow]:
    rows: list[ParsedResultRow] = []
    for li in soup.find_all("li"):
        texts = [segment.strip() for segment in li.stripped_strings if segment.strip()]
        if len(texts) < 3:
            continue
        place = _parse_int(texts[0])
        if place is None:
            continue
        pilot = _extract_pilot(texts)
        time_value = _extract_time(texts)
        if pilot and time_value is not None:
            rows.append(
                ParsedResultRow(
                    pilot=pilot,
                    country=_extract_country(texts),
                    category=_extract_list_category(li),
                    quad=_extract_quad(texts),
                    time=time_value,
                    points=_parse_last_int(texts),
                    place=place,
                ),
            )
    return _deduplicate_result_rows(rows)


def _extract_season_rows_from_list_items(soup: BeautifulSoup) -> list[ParsedSeasonRow]:
    rows: list[ParsedSeasonRow] = []
    season_mode = False
    for node in soup.find_all(["h1", "h2", "h3", "h4", "li"]):
        if node.name != "li":
            heading = node.get_text(" ", strip=True).lower()
            if "season" in heading and "leaderboard" in heading:
                season_mode = True
            continue
        if not season_mode:
            continue
        texts = [segment.strip() for segment in node.stripped_strings if segment.strip()]
        if len(texts) < 2:
            continue
        place = _parse_int(texts[0])
        pilot = _extract_pilot(texts)
        points = _parse_last_int(texts)
        if pilot and points is not None:
            rows.append(
                ParsedSeasonRow(
                    pilot=pilot,
                    country=_extract_country(texts),
                    category=_extract_list_category(node),
                    points=points,
                    place=place,
                ),
            )
    return _deduplicate_season_rows(rows)


def _extract_results_from_leaderboard_sections(soup: BeautifulSoup) -> list[ParsedResultRow]:
    section_root = _find_leaderboard_root(soup, "TODAY'S LEADERBOARD")
    if section_root is None:
        return []

    rows: list[ParsedResultRow] = []
    category_blocks = _extract_category_blocks(section_root)
    if category_blocks:
        for category, block in category_blocks:
            rows.extend(_extract_current_rows_from_block(block, category))
    else:
        rows.extend(_extract_current_rows_from_block(section_root, None))
    return _deduplicate_result_rows(rows)


def _extract_season_rows_from_leaderboard_sections(soup: BeautifulSoup) -> list[ParsedSeasonRow]:
    section_root = _find_leaderboard_root(soup, "SEASON LEADERBOARD")
    if section_root is None:
        return []

    rows: list[ParsedSeasonRow] = []
    category_blocks = _extract_category_blocks(section_root)
    if category_blocks:
        for category, block in category_blocks:
            rows.extend(_extract_season_rows_from_block(block, category))
    else:
        rows.extend(_extract_season_rows_from_block(section_root, None))
    return _deduplicate_season_rows(rows)


def _find_leaderboard_root(soup: BeautifulSoup, heading_text: str):
    heading = soup.find(
        lambda tag: tag.name == "h3" and heading_text.lower() in tag.get_text(" ", strip=True).lower(),
    )
    if heading is None:
        return None

    current = heading.parent
    while current is not None:
        sibling = current.find_next_sibling()
        if sibling is not None:
            return sibling
        current = current.parent
    return None


def _extract_category_blocks(section_root) -> list[tuple[str | None, Any]]:
    blocks: list[tuple[str | None, Any]] = []
    for block in section_root.find_all("div", recursive=False):
        if "overflow-hidden" not in (block.get("class") or []):
            continue
        category = _extract_block_category(block)
        blocks.append((category, block))
    if blocks:
        return blocks

    nested_wrapper = section_root.find("div", class_=lambda value: value and "flex" in value and "gap-6" in value)
    if nested_wrapper is None:
        return []
    for block in nested_wrapper.find_all("div", recursive=False):
        if "overflow-hidden" not in (block.get("class") or []):
            continue
        blocks.append((_extract_block_category(block), block))
    return blocks


def _extract_block_category(block) -> str | None:
    category_span = block.find("span", string=lambda text: text and text.strip().lower() in CATEGORY_NAMES)
    if category_span is None:
        return None
    return category_span.get_text(" ", strip=True).lower()


def _extract_current_rows_from_block(block, category: str | None) -> list[ParsedResultRow]:
    rows: list[ParsedResultRow] = []
    for item in block.find_all("li"):
        place_node = item.find("span")
        pilot_node = item.find("a")
        quad_node = item.find("p")
        time_node = _find_value_node(item, expect_points=False)
        points_node = _find_points_node(item)

        pilot = pilot_node.get_text(" ", strip=True) if pilot_node else None
        if not pilot:
            continue

        rows.append(
            ParsedResultRow(
                pilot=pilot,
                country=_extract_country_from_item(item),
                category=category,
                quad=quad_node.get_text(" ", strip=True) if quad_node else None,
                time=_parse_float(time_node.get_text(" ", strip=True)) if time_node else None,
                points=_parse_int(points_node.get_text(" ", strip=True)) if points_node else None,
                place=_parse_int(place_node.get_text(" ", strip=True)) if place_node else None,
            ),
        )
    return rows


def _extract_season_rows_from_block(block, category: str | None) -> list[ParsedSeasonRow]:
    rows: list[ParsedSeasonRow] = []
    for item in block.find_all("li"):
        place_node = item.find("span")
        pilot_node = item.find("a")
        points_node = _find_value_node(item, expect_points=True)

        pilot = pilot_node.get_text(" ", strip=True) if pilot_node else None
        if not pilot:
            continue

        rows.append(
            ParsedSeasonRow(
                pilot=pilot,
                country=_extract_country_from_item(item),
                category=category,
                points=_parse_int(points_node.get_text(" ", strip=True)) if points_node else None,
                place=_parse_int(place_node.get_text(" ", strip=True)) if place_node else None,
            ),
        )
    return rows


def _extract_country_from_item(item) -> str | None:
    flag = item.find(
        lambda tag: tag.name == "span" and any(class_name.startswith("fi-") for class_name in (tag.get("class") or [])),
    )
    if flag is None:
        return None
    title = flag.get("title")
    if not title:
        return None
    normalized = str(title).strip().upper()
    if len(normalized) in {2, 3} and normalized.isalpha():
        return normalized
    return None


def _find_value_node(item, *, expect_points: bool):
    value_nodes = item.find_all(
        lambda tag: tag.name == "div" and "tabular-nums" in " ".join(tag.get("class") or []),
    )
    if not value_nodes:
        return None
    if expect_points:
        return value_nodes[-1]
    return value_nodes[0]


def _find_points_node(item):
    value_nodes = item.find_all(
        lambda tag: tag.name == "div" and "tabular-nums" in " ".join(tag.get("class") or []),
    )
    if len(value_nodes) < 2:
        return None
    candidate = value_nodes[-1]
    candidate_text = candidate.get_text(" ", strip=True)
    if _parse_int(candidate_text) is not None:
        return candidate
    return None


def _extract_list_category(node) -> str | None:
    current = node
    while current is not None:
        previous = current.find_previous(["h1", "h2", "h3", "h4"])
        if previous is None:
            return None
        heading = previous.get_text(" ", strip=True).lower()
        if heading in CATEGORY_NAMES:
            return heading
        if "season" in heading or "leaderboard" in heading:
            return None
        current = previous
    return None


def _deduplicate_result_rows(rows: list[ParsedResultRow]) -> list[ParsedResultRow]:
    unique: dict[tuple[str, int | None, str | None], ParsedResultRow] = {}
    for row in rows:
        unique[(row.pilot, row.place, row.category)] = row
    return list(unique.values())


def _deduplicate_season_rows(rows: list[ParsedSeasonRow]) -> list[ParsedSeasonRow]:
    unique: dict[tuple[str, int | None, str | None], ParsedSeasonRow] = {}
    for row in rows:
        unique[(row.pilot, row.place, row.category)] = row
    return list(unique.values())


def _extract_dashboard_payload_from_scripts(soup: BeautifulSoup) -> dict[str, Any] | None:
    for script in soup.find_all("script"):
        script_text = script.string or script.get_text(strip=False)
        if not script_text:
            continue
        payload = _extract_dashboard_payload_from_json_blob(script_text)
        if payload is not None:
            return payload
    return None


def _extract_dashboard_payload_from_json_blob(text: str) -> dict[str, Any] | None:
    normalized = text.strip()
    candidate_objects: list[dict[str, Any]] = []
    if normalized.startswith("{") or normalized.startswith("["):
        try:
            data = json.loads(normalized)
            if isinstance(data, dict):
                candidate_objects.append(data)
        except json.JSONDecodeError:
            pass

    for match in re.finditer(r"\{.*?\}", text, flags=re.DOTALL):
        snippet = match.group(0)
        if "\"leaderboard\"" not in snippet and "\"seasonLeaderboard\"" not in snippet:
            continue
        try:
            data = json.loads(snippet)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            candidate_objects.append(data)

    for item in candidate_objects:
        if _looks_like_dashboard_payload(item):
            return item
    return None


def _looks_like_dashboard_payload(payload: dict[str, Any]) -> bool:
    return any(key in payload for key in ("leaderboard", "seasonLeaderboard", "competition"))


def _parse_dashboard_payload(
    *,
    dashboard_payload: dict[str, Any],
    target_date: date,
    race_class: str,
    source: str,
) -> ParsedDayPayload:
    competition = dashboard_payload.get("competition") or {}
    season = dashboard_payload.get("season") or target_date.strftime("%Y-%m")
    track = competition.get("trackName") or competition.get("mapName") or "Unknown track"
    quad_of_the_day = competition.get("quadOfTheDay")

    results: list[ParsedResultRow] = []
    for group in dashboard_payload.get("leaderboard") or []:
        category = _normalize_category(group.get("league"))
        for row in group.get("results") or []:
            results.append(
                ParsedResultRow(
                    pilot=(row.get("playerName") or "").strip(),
                    country=_normalize_country(row.get("country")),
                    category=category,
                    quad=(row.get("modelName") or None),
                    time=_normalize_track_time(row.get("trackTime")),
                    points=_normalize_int(row.get("points")),
                    place=_normalize_int(row.get("localRank") or row.get("rank")),
                ),
            )

    season_leaderboard: list[ParsedSeasonRow] = []
    for group in dashboard_payload.get("seasonLeaderboard") or []:
        category = _normalize_category(group.get("league"))
        for row in group.get("results") or []:
            season_leaderboard.append(
                ParsedSeasonRow(
                    pilot=(row.get("playerName") or "").strip(),
                    country=_normalize_country(row.get("country")),
                    category=category,
                    points=_normalize_int(row.get("points")),
                    place=_normalize_int(row.get("rank") or row.get("localRank")),
                ),
            )

    return ParsedDayPayload(
        date=target_date,
        race_class=race_class,
        season=str(season),
        track=str(track),
        quad_of_the_day=quad_of_the_day,
        results=_deduplicate_result_rows([row for row in results if row.pilot]),
        season_leaderboard=_deduplicate_season_rows([row for row in season_leaderboard if row.pilot]),
        source=source,
    )


def _normalize_category(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    return text if text in CATEGORY_NAMES else None


def _normalize_country(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().upper()
    if len(text) in {2, 3} and text.isalpha():
        return text
    return None


def _normalize_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    return _parse_int(str(value))


def _normalize_track_time(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        numeric = float(value)
        if numeric > 1000:
            return round(numeric / 1000.0, 3)
        return round(numeric, 3)
    return _parse_float(str(value))

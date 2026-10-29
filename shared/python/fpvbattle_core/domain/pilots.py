from __future__ import annotations

from types import MappingProxyType


# Keep renamed accounts here so the database has one stable identity per pilot.
# Keys are compared case-insensitively, while the value is the name shown in the UI.
PILOT_ALIASES = MappingProxyType(
    {
        "ol_ek": "dronovoda",
    },
)


def canonicalize_pilot_name(pilot: str) -> str:
    """Return the canonical identity for a source-provided pilot name."""
    canonical = pilot.strip()
    canonical_names = {name.casefold(): name for name in PILOT_ALIASES.values()}
    canonical = canonical_names.get(canonical.casefold(), canonical)
    seen: set[str] = set()
    while canonical.casefold() in PILOT_ALIASES and canonical.casefold() not in seen:
        seen.add(canonical.casefold())
        canonical = PILOT_ALIASES[canonical.casefold()]
    return canonical

"""Resolve display flight status from telemetry + commercial metadata."""

from __future__ import annotations

# Values that only mean "airborne" without extra semantics.
_GENERIC_AIRBORNE = frozenset(
    {
        "",
        "enroute",
        "en_route",
        "en-route",
        "active",
        "flying",
        "airborne",
        "departed",
    }
)


def _normalize(raw: str | None) -> str:
    if not raw:
        return ""
    return raw.strip().lower().replace("-", "_")


def is_on_ground(
    *,
    on_ground: bool | None = None,
    altitude_ft: int | None = None,
) -> bool | None:
    """Return True/False when ground state is known, else None."""
    if on_ground is not None:
        return on_ground
    if altitude_ft is None:
        return None
    return altitude_ft <= 100


def resolve_flight_status(
    raw_status: str | None,
    *,
    altitude_ft: int | None = None,
    on_ground: bool | None = None,
) -> str:
    """Canonical status codes: ground | en-route | landed | scheduled | cancelled | diverted | delayed."""
    norm = _normalize(raw_status)
    grounded = is_on_ground(on_ground=on_ground, altitude_ft=altitude_ft)

    if grounded is True:
        if norm in ("landed", "arrived"):
            return "landed"
        if norm in ("scheduled",):
            return "scheduled"
        if norm in ("cancelled", "canceled"):
            return "cancelled"
        if norm in ("diverted",):
            return "diverted"
        if norm in ("delayed",):
            return "delayed"
        return "ground"

    if grounded is False:
        if norm in ("landed", "arrived"):
            return "landed"
        if norm in ("scheduled",):
            return "scheduled"
        if norm in ("cancelled", "canceled"):
            return "cancelled"
        if norm in ("diverted",):
            return "diverted"
        if norm in ("delayed",):
            return "delayed"
        return "en-route"

    # Altitude unknown — keep explicit commercial states, else generic airborne.
    if norm and norm not in _GENERIC_AIRBORNE:
        if norm in ("landed", "arrived"):
            return "landed"
        if norm == "scheduled":
            return "scheduled"
        if norm in ("cancelled", "canceled"):
            return "cancelled"
        if norm == "diverted":
            return "diverted"
        if norm == "delayed":
            return "delayed"
        return norm.replace("_", "-")

    return "en-route"

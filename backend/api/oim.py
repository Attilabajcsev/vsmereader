import json
import logging
from typing import Any, Dict, Iterable, Tuple

logger = logging.getLogger(__name__)


def _get(obj: Dict[str, Any], *keys: str) -> Any:
    for k in keys:
        if k in obj:
            return obj[k]
    return None


def _format_period(dimensions: Dict[str, Any], fact: Dict[str, Any]) -> str:
    # Try common OIM encodings for period/instant
    period = _get(fact, "p", "period") or _get(dimensions, "period") or {}
    if isinstance(period, dict):
        start = _get(period, "start", "s", "startDate")
        end = _get(period, "end", "e", "endDate")
        instant = _get(period, "instant", "i")
        if start and end:
            return f"{start} to {end}"
        if instant:
            return f"{instant}"
    if isinstance(period, list) and len(period) == 2:
        return f"{period[0]} to {period[1]}"
    if isinstance(period, str):
        return period
    # Some formats put instant directly on fact
    instant = _get(fact, "i", "instant")
    if instant:
        return str(instant)
    return ""


def _format_entity(dimensions: Dict[str, Any], fact: Dict[str, Any]) -> str:
    entity = _get(fact, "entity", "e") or _get(dimensions, "entity") or {}
    if isinstance(entity, dict):
        ident = _get(entity, "identifier", "id")
        scheme = _get(entity, "scheme", "sch")
        if ident and scheme:
            return f"{ident}"
        if ident:
            return str(ident)
    if isinstance(entity, str):
        return entity
    return ""


def extract_metadata(oim_json: Dict[str, Any]) -> Tuple[str, str]:
    """Return (entity, period) best-effort from the first fact."""
    facts = oim_json.get("facts") or {}
    if isinstance(facts, dict):
        for _, fact in facts.items():
            if not isinstance(fact, dict):
                continue
            dimensions = fact.get("d") or fact.get("dimensions") or {}
            entity = _format_entity(dimensions, fact)
            period = _format_period(dimensions, fact)
            return entity or "", period or ""
    elif isinstance(facts, list):
        for fact in facts:
            if not isinstance(fact, dict):
                continue
            dimensions = fact.get("d") or fact.get("dimensions") or {}
            entity = _format_entity(dimensions, fact)
            period = _format_period(dimensions, fact)
            return entity or "", period or ""
    return "", ""


def extract_facts(oim_json: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    """Yield simplified fact rows with concept, value, datatype, unit, context."""
    facts = oim_json.get("facts")
    if isinstance(facts, dict):
        items = facts.items()
    elif isinstance(facts, list):
        items = enumerate(facts)
    else:
        logger.warning("OIM JSON has no 'facts' object")
        return []

    rows = []
    for _, fact in items:
        if not isinstance(fact, dict):
            continue
        dimensions = fact.get("d") or fact.get("dimensions") or {}
        concept = _get(fact, "c", "concept") or _get(dimensions, "concept") or ""
        value = _get(fact, "v", "value")
        dtype = _get(fact, "xdt", "datatype", "type") or ""
        unit = _get(fact, "u", "unit") or _get(dimensions, "unit") or ""
        context = _format_period(dimensions, fact)
        # Stringify complex values safely
        if isinstance(value, (dict, list)):
            try:
                value = json.dumps(value, ensure_ascii=False)
            except Exception:
                value = str(value)
        rows.append(
            {
                "concept": str(concept),
                "value": "" if value is None else str(value),
                "datatype": str(dtype),
                "unit": str(unit),
                "context": str(context),
            }
        )
    return rows


def extract_reporting_year_from_period(reporting_period: str) -> int | None:
    """Extract a reporting year from a period string like '2024-01-01 to 2024-12-31' or '2024-12-31' or '2025-01-01T00:00:00/2026-01-01T00:00:00'."""
    if not reporting_period:
        return None
    
    import re
    # Look for 4-digit years in the period string
    years = re.findall(r'\b(20\d{2}|19\d{2})\b', reporting_period)
    if years:
        # For XBRL period ranges like "2025-01-01T00:00:00/2026-01-01T00:00:00"
        # the reporting year is the start year (2025), not the end year (2026)
        if len(years) >= 2 and '/' in reporting_period:
            # This is likely a range period - use the first year
            return int(years[0])
        else:
            # Single date or other format - return the last/most recent year found
            return int(years[-1])
    return None


def quick_extract_metadata_from_file(file_path: str) -> Tuple[str, str, int | None]:
    """
    Quick extraction of entity, period, and year from an uploaded file.
    Returns (entity_name, reporting_period, reporting_year).
    This is a best-effort approach for pre-processing validation.
    """
    try:
        import tempfile
        import os
        import shutil
        
        # We'll attempt a simpler approach - try to avoid the full Arelle processing for now
        # and fallback to a basic filename/content analysis
        
        # For now, return empty values to prevent processing errors
        # The full processing will still extract this information later
        logger.info("Quick metadata extraction skipped for file: %s", file_path)
        return "", "", None
        
    except Exception as e:
        logger.warning("Quick metadata extraction failed: %s", e)
    
    return "", "", None



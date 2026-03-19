"""
Eco-Pulse V3.0 — Carbon Impact Lookup
Green DB lookup with AI fallback for unknown items.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger("ecopulse.carbon")


async def lookup_carbon_impact(
    item_name: str,
    category: str,
    db_module=None,
    ai_client=None,
    settings=None,
) -> float:
    """
    Look up the CO₂ impact for an item:
    1. Check the carbon_impact_db table (fuzzy match on item_name)
    2. If not found → ask Gemini to estimate the CO₂/unit
    3. Persist the AI estimate back into carbon_impact_db for future lookups
    """
    if db_module is None:
        import database as db_module  # noqa: F811

    # Step 1 — local lookup (exact or fuzzy)
    match = await db_module.fuzzy_match_carbon_db(item_name)
    if match:
        return match["co2_per_unit_kg"]

    # Step 2 — AI estimate for unknown item
    if ai_client is not None and settings is not None:
        try:
            from google.genai import types
            from schemas import CarbonEstimate

            response = ai_client.models.generate_content(
                model=settings.model_name,
                contents=(
                    f"Estimate the carbon footprint (kg CO₂ per unit) for: "
                    f"{item_name} (category: {category}). "
                    f"Base your estimate on lifecycle analysis data. "
                    f"Return ONLY JSON matching the schema."
                ),
                config={
                    "response_mime_type": "application/json",
                    "response_json_schema": CarbonEstimate.model_json_schema(),
                },
            )

            estimate = CarbonEstimate.model_validate_json(response.text)

            # Step 3 — persist so future lookups are instant
            await db_module.insert_carbon_item(
                item_name=item_name,
                category=category,
                co2_per_unit_kg=estimate.co2_per_unit_kg,
                avg_shelf_life_days=estimate.avg_shelf_life_days,
            )
            await db_module.log_audit(
                "CARBON_AI_ESTIMATE",
                severity="INFO",
                details={
                    "item": item_name,
                    "co2": estimate.co2_per_unit_kg,
                    "note": "AI-estimated, persisted to Green DB",
                },
            )
            return estimate.co2_per_unit_kg

        except Exception as exc:
            logger.warning("Carbon AI estimate failed for %s: %s", item_name, exc)
            await db_module.log_audit(
                "CARBON_LOOKUP_FAILED",
                severity="WARN",
                details={"item": item_name, "error": str(exc)},
            )

    # Fallback — 0.0 (will be updated when data becomes available)
    return 0.0


async def estimate_expiry_date(
    item_name: str,
    from_date: str | None = None,
    db_module=None,
) -> str | None:
    """
    Estimate an expiry date for an item based on avg_shelf_life_days
    from the carbon_impact_db.  Returns ISO date string or None.
    """
    from datetime import datetime, timedelta

    if db_module is None:
        import database as db_module  # noqa: F811

    match = await db_module.fuzzy_match_carbon_db(item_name)
    if not match:
        return None

    shelf_life = match.get("avg_shelf_life_days")
    if not shelf_life or int(shelf_life) <= 0:
        return None  # non-perishable

    if from_date:
        base = datetime.fromisoformat(from_date)
    else:
        try:
            from dev_mode import get_current_date
            base = await get_current_date()
        except Exception:
            base = datetime.now()

    return (base + timedelta(days=int(shelf_life))).strftime("%Y-%m-%d")

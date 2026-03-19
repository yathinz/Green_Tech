"""
Eco-Pulse V3.0 — FastAPI Application
Main entry-point with all endpoints, startup events, and background tasks.
"""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, File, Form, Query, UploadFile
from fastapi.responses import JSONResponse

import database as db
from config import settings, validate_settings
from schemas import (
    ForecastResult,
    HealthResponse,
    IngestionResponse,
)

# ── Logging ──────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(name)-25s | %(levelname)-5s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ecopulse.main")

# ── Background task handle ───────────────────────────────
_scheduler_task: Optional[asyncio.Task] = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Lifespan
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    global _scheduler_task

    # Startup
    validate_settings()
    await db.init_db(settings.database_path)
    logger.info("🚀 Eco-Pulse V3.1 started (dev_mode=%s)", settings.dev_mode)

    # Start forecast scheduler in background
    from predictive_math import forecast_scheduler

    _scheduler_task = asyncio.create_task(forecast_scheduler(interval_seconds=3600))

    yield

    # Shutdown
    if _scheduler_task:
        _scheduler_task.cancel()
        try:
            await _scheduler_task
        except asyncio.CancelledError:
            pass
    logger.info("Eco-Pulse shutdown complete")


app = FastAPI(
    title="Eco-Pulse V3.0 — Zero-Waste Inventory Engine",
    description="AI-powered inventory lifecycle manager with CLI-first interface",
    version="3.1",
    lifespan=lifespan,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Ingestion Endpoints
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@app.post("/ingest/image", response_model=IngestionResponse, status_code=202)
async def ingest_image(
    file: UploadFile = File(...),
    multiplier: float = Form(1.0, description="Quantity multiplier — scales all extracted quantities (e.g. 2.0 doubles them)"),
):
    """Upload a receipt/shelf image for AI extraction with optional quantity multiplier."""
    # Save uploaded file to temp path
    suffix = os.path.splitext(file.filename or "image.jpg")[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    task_id = str(uuid.uuid4())

    _mult = multiplier

    async def _process():
        try:
            from ai_service import process_input
            await process_input(tmp_path, "IMAGE", multiplier=_mult)
        finally:
            os.unlink(tmp_path)

    asyncio.create_task(_process())
    mult_msg = f" (multiplier: {_mult}x)" if _mult != 1.0 else ""
    return IngestionResponse(task_id=task_id, status="PROCESSING", message=f"Image queued for extraction{mult_msg}")


@app.post("/ingest/voice", response_model=IngestionResponse, status_code=202)
async def ingest_voice(file: UploadFile = File(...)):
    """Upload an audio file for AI extraction."""
    suffix = os.path.splitext(file.filename or "audio.wav")[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    task_id = str(uuid.uuid4())

    async def _process():
        try:
            from ai_service import process_input
            await process_input(tmp_path, "VOICE")
        finally:
            os.unlink(tmp_path)

    asyncio.create_task(_process())
    return IngestionResponse(task_id=task_id, status="PROCESSING", message="Audio queued for extraction")


@app.post("/ingest/text", response_model=IngestionResponse, status_code=202)
async def ingest_text(text: str = Form(...)):
    """Natural language text input for AI extraction."""
    task_id = str(uuid.uuid4())

    async def _process():
        from ai_service import process_input
        await process_input(text, "TEXT")

    asyncio.create_task(_process())
    return IngestionResponse(task_id=task_id, status="PROCESSING", message="Text queued for extraction")


@app.post("/ingest/csv")
async def ingest_csv(file: UploadFile = File(...)):
    """Bulk CSV import with automatic CO₂ lookup and expiry estimation."""
    import csv
    import io

    from carbon_lookup import estimate_expiry_date, lookup_carbon_impact

    content = (await file.read()).decode("utf-8")
    reader = csv.DictReader(io.StringIO(content))
    count = 0
    for row in reader:
        item_name = row.get("item_name", "unknown")
        category = row.get("category", "Other")

        # ── CO₂: use CSV value if provided, otherwise look up from carbon DB
        raw_co2 = row.get("co2_per_unit_kg", "").strip()
        if raw_co2:
            co2 = float(raw_co2)
        else:
            co2 = await lookup_carbon_impact(item_name, category)

        # ── Expiry: use CSV value if provided, otherwise estimate from shelf life
        expiry = row.get("expiry_date", "").strip() or None
        if not expiry:
            expiry = await estimate_expiry_date(item_name)

        await db.insert_inventory_item(
            item_name=item_name,
            category=category,
            quantity=float(row.get("quantity", 0)),
            unit=row.get("unit", "units"),
            expiry_date=expiry,
            co2_per_unit_kg=co2,
            confidence_score=1.0,
            input_method="CSV_IMPORT",
        )
        count += 1
    return {"status": "OK", "items_imported": count}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Inventory CRUD
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@app.get("/inventory")
async def list_inventory(
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    """List all inventory items with optional filters."""
    items = await db.get_all_items(category=category, status=status, search=search)
    return {"items": items, "count": len(items)}


@app.get("/inventory/search")
async def search_inventory(q: str = Query(...)):
    """Full-text search of inventory."""
    items = await db.search_items(q)
    return {"items": items, "count": len(items)}


@app.get("/inventory/{item_id}")
async def get_inventory_item(item_id: str):
    """Get a single inventory item."""
    item = await db.get_item(item_id)
    if not item:
        return JSONResponse(status_code=404, content={"error": "Item not found"})
    return item


@app.put("/inventory/{item_id}")
async def update_inventory_item(item_id: str, quantity: Optional[float] = None, status: Optional[str] = None):
    """Update an inventory item."""
    item = await db.get_item(item_id)
    if not item:
        return JSONResponse(status_code=404, content={"error": "Item not found"})
    updates = {}
    if quantity is not None:
        updates["quantity"] = quantity
    if status is not None:
        updates["status"] = status
    if updates:
        await db.update_inventory_item(item_id, **updates)
    return await db.get_item(item_id)


@app.delete("/inventory/{item_id}", status_code=204)
async def delete_inventory_item(item_id: str):
    """Remove an inventory item."""
    await db.delete_item(item_id)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Review Queue
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@app.get("/review")
async def list_reviews():
    """List pending review items."""
    reviews = await db.get_pending_reviews()
    return {"items": reviews, "count": len(reviews)}


@app.post("/review/{review_id}/approve")
async def approve_review(review_id: str):
    """Approve and move to active inventory."""
    item_id = await db.approve_review(review_id)
    if item_id:
        return {"status": "approved", "item_id": item_id}
    return JSONResponse(status_code=404, content={"error": "Review not found"})


@app.post("/review/{review_id}/reject", status_code=204)
async def reject_review(review_id: str):
    """Reject and discard."""
    await db.reject_review(review_id)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Triage & Forecast
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@app.get("/triage")
async def get_triage():
    """Get FEFO-ordered expiring items + AI recipes."""
    expiring = await db.get_items_expiring_within(days=7)
    recipes = await db.get_recent_recipes(limit=5)
    return {
        "expiring_items": expiring,
        "expiring_count": len(expiring),
        "recent_recipes": recipes,
    }


@app.post("/triage/generate-recipes")
async def generate_recipes():
    """Force recipe generation for expiring items."""
    from ai_service import generate_recipes_with_ai

    expiring = await db.get_items_expiring_within(days=7)
    if not expiring:
        return {"message": "No items expiring within 7 days", "recipes": []}

    try:
        response = await generate_recipes_with_ai(expiring)
        # Build a lookup of co2 per unit by item name
        co2_lookup = {item["item_name"].lower(): item.get("co2_per_unit_kg", 0) for item in expiring}

        for recipe in response.recipes:
            # CO2 saved = sum of (quantity_used × co2_per_unit) for items diverted from waste
            co2_saved = 0.0
            for ingredient_name, qty_used in recipe.quantities_used.items():
                co2_rate = co2_lookup.get(ingredient_name.lower(), 0)
                co2_saved += co2_rate * qty_used

            await db.insert_recipe(
                title=recipe.title,
                ingredients_used=recipe.ingredients_used,
                instructions=recipe.instructions,
                estimated_servings=recipe.estimated_servings,
                co2_saved_kg=round(co2_saved, 2),
                original_price=recipe.original_price,
                suggested_price=recipe.suggested_price,
                discount_percent=recipe.discount_percent,
                ai_generated=True,
            )
        return {
            "message": f"Generated {len(response.recipes)} recipe(s)",
            "recipes": [r.model_dump() for r in response.recipes],
        }
    except Exception as exc:
        return {"message": f"Recipe generation failed: {exc}", "recipes": []}


@app.get("/forecast")
async def get_all_forecasts():
    """Forecast all items with burn-rates."""
    forecasts = await db.get_all_forecasts()
    return {"forecasts": forecasts, "count": len(forecasts)}


@app.post("/forecast/refresh")
async def refresh_all_forecasts():
    """Recalculate and persist forecasts for all active items."""
    from predictive_math import update_all_forecasts

    count = await update_all_forecasts()
    forecasts = await db.get_all_forecasts()
    return {"message": f"Refreshed {count} forecast(s)", "forecasts": forecasts, "count": count}


@app.get("/forecast/{item_id}")
async def get_item_forecast(item_id: str):
    """Forecast a specific item."""
    from predictive_math import forecast_burn_rate

    result = await forecast_burn_rate(item_id)
    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Community Mesh — Donation Partner Matching
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@app.get("/community-mesh/partners")
async def list_partners():
    """List all registered donation partners."""
    partners = await db.get_all_partners()
    return {"partners": partners, "count": len(partners)}


@app.get("/community-mesh/matches")
async def find_donation_matches(days: int = Query(7, ge=1, le=30)):
    """Find expiring items with matching donation partners (FEFO order)."""
    matches = await db.find_donation_matches(days=days)
    return {"matches": matches, "count": len(matches)}


@app.post("/community-mesh/donate/{item_id}")
async def donate_item(item_id: str, partner: str = Form(...)):
    """Donate an item to a community partner. Logs mock email and marks DONATED."""
    result = await db.record_donation(item_id=item_id, partner_name=partner)
    if "error" in result:
        return JSONResponse(status_code=404, content=result)
    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  System Endpoints
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """System health check."""
    from dev_mode import get_current_date

    sim_date = await db.get_config("simulated_date")
    return HealthResponse(
        status="healthy",
        database="connected",
        ai_api="configured" if settings.gemini_api_key else "not_configured",
        dev_mode=settings.dev_mode,
        simulated_date=sim_date if sim_date else None,
    )


@app.get("/audit-log")
async def get_audit_log(event_type: Optional[str] = None, limit: int = 50):
    """View audit trail."""
    logs = await db.get_audit_logs(event_type=event_type, limit=limit)
    return {"logs": logs, "count": len(logs)}


@app.get("/metrics")
async def get_metrics():
    """Carbon impact summary."""
    return await db.get_carbon_metrics()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Dev Mode Endpoints
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@app.post("/dev/advance-time")
async def dev_advance_time(days: int = Form(...)):
    """Advance simulated time by N days."""
    from dev_mode import advance_time

    new_date = await advance_time(days)
    expiring = await db.get_items_expiring_within(days=3)
    return {
        "new_simulated_date": new_date,
        "items_now_expiring_soon": len(expiring),
    }


@app.post("/dev/seed-data")
async def dev_seed_data():
    """Seed synthetic data."""
    try:
        import sys
        sys.path.insert(0, "/app")
        from scripts.seed_database import seed_all
        summary = await seed_all(settings.database_path)
        return {"status": "OK", "summary": summary}
    except Exception as exc:
        return {"status": "ERROR", "error": str(exc)}


@app.post("/dev/reset")
async def dev_reset():
    """Reset the database."""
    await db.reset_database()
    return {"status": "OK", "message": "Database reset complete"}

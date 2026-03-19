"""
Eco-Pulse V3.0 — AI Service
Gemini 2.5 Flash integration: 3 input modes, 5 fallback paths,
recipe generation, and community mesh stub.
"""

from __future__ import annotations

import asyncio
import json
import logging
import mimetypes
import time
from datetime import datetime
from typing import Any, Callable, Optional

logger = logging.getLogger("ecopulse.ai")

# Late imports — only available inside Docker with google-genai installed
_client = None


def _get_client():
    global _client
    if _client is None:
        try:
            from google import genai
            from config import settings

            _client = genai.Client(api_key=settings.gemini_api_key)
        except Exception as exc:
            logger.error("Cannot initialise Gemini client: %s", exc)
    return _client


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Prompts
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EXTRACTION_PROMPT = """
You are an inventory data extraction assistant for a small business/cafe/non-profit.

Extract ALL inventory items from the provided input (image, audio, or text).
For images of shelves please check how many items are actually there, even the ones that are hidden behind others. For receipts, extract the full quantity purchased, not just what's currently visible.

For each item, determine:
- item_name: The CANONICAL, SINGULAR, LOWERCASE English name of the item.
  Rules: always singular ("apple" not "apples"), use standard US English spelling
  ("aluminum" not "aluminium"), no brand names unless essential, be specific
  ("whole milk" not just "milk", "basmati rice" not just "rice").
- quantity: Convert to the BASE METRIC UNIT quantity as a float.
  Rules: Convert cups/tablespoons/packs to grams or mL using standard conversions.
  Examples: "1 cup of rice" → 185 (grams), "1 pack of butter (250g)" → 250 (grams),
  "2 dozen eggs" → 24 (units), "1 gallon milk" → 3.785 (L).
  If a "pack" has no clear weight, estimate based on typical retail pack size for that item.
- unit: The CANONICAL base unit after conversion. Use ONLY: kg, g, L, mL, units.
  Rules: Solids in g or kg, liquids in mL or L, countable items in "units".
  Never use "packs", "bottles", "cans", "boxes" — convert to the underlying quantity.
- raw_input_text: The original text as it appeared in the input (for audit trail).
- category: The granular category. Choose from:
  Dairy: "Milk & Cream", "Cheese", "Yogurt", "Butter & Spreads", "Eggs"
  Produce: "Fresh Fruit", "Fresh Vegetables", "Herbs & Leafy Greens", "Root Vegetables"
  Protein: "Poultry", "Red Meat", "Seafood"
  Bakery: "Bread & Rolls", "Pastry & Cakes"
  Pantry: "Grains & Rice", "Pasta & Noodles", "Cooking Oils & Vinegar",
          "Condiments & Sauces", "Sugar & Sweeteners", "Nuts & Seeds", "Canned & Preserved"
  Beverages: "Coffee & Tea", "Juice & Soft Drinks", "Plant-Based Milk"
  Non-food: "Office - Paper", "Office - Supplies", "Cleaning Products",
            "Lab Chemicals", "Lab Equipment", "Other"
- expiry_date: The expiration date in YYYY-MM-DD format. If a relative date is given
  (e.g., "next Tuesday", "in 5 days"), calculate from today's date: {current_date}.
  If no expiry is mentioned and the item is perishable, estimate a reasonable shelf life.
  If the item is non-perishable, set to null.
- confidence_score: Your confidence in this extraction (0.0 to 1.0).
  Be HONEST. If the input is unclear, blurry, or ambiguous, give a LOW score.
  If you had to estimate a pack size or convert an ambiguous unit, lower the score.

Also provide a brief source_description of what the input contained.

IMPORTANT: If you're unsure about an item, still include it but with a low confidence_score.
Do NOT hallucinate items that aren't in the input.
"""

RECIPE_PROMPT = """
You are a creative chef assistant helping a small cafe reduce food waste.

The following items are expiring soon and MUST be used up completely:
{expiring_items_json}

Generate AT LEAST 3 practical recipes that COLLECTIVELY use up ALL the quantities listed above.
Every single unit of every item must be allocated across the recipes.

For example, if there are 36 eggs, your 3+ recipes combined must use exactly 36 eggs total
(e.g. Recipe 1 uses 12 eggs, Recipe 2 uses 18 eggs, Recipe 3 uses 6 eggs).

Rules:
1. Each recipe MUST specify the exact quantity of each expiring item it uses
2. The SUM of quantities across all recipes for each item must EQUAL the available quantity
3. Recipes should be practical for a small cafe kitchen
4. Prioritize recipes that use the MOST URGENTLY expiring items
5. Could be sold as a "Special of the Day"
6. Minimize additional ingredient purchases
7. For EVERY recipe, suggest a discounted menu price and discount percentage.
   The discount should incentivize customers to buy the dish before ingredients expire.
   Base the price on typical cafe menu pricing for similar dishes, then apply a
   discount (15–40%) depending on urgency (more discount = closer to expiry).

For each recipe, specify:
- title: recipe name
- ingredients_used: list of expiring item NAMES used
- quantities_used: dict mapping each ingredient name to the quantity used (number only)
- additional_ingredients: any non-expiring items needed
- instructions: step-by-step cooking instructions
- estimated_servings: number of servings
- difficulty: Easy, Medium, or Hard
- original_price: the normal menu price for this dish (number, e.g. 12.99)
- suggested_price: the discounted price to sell at (number, e.g. 8.99)
- discount_percent: the discount percentage applied (integer, e.g. 30)
"""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Core Gemini wrapper
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def call_gemini(
    contents: list[Any],
    schema: dict,
    model_name: str | None = None,
) -> str:
    """
    Call Gemini with structured JSON output.
    Returns the raw JSON text response.
    """
    from config import settings

    client = _get_client()
    if client is None:
        raise ConnectionError("Gemini client is not initialised")

    model = model_name or settings.model_name

    response = client.models.generate_content(
        model=model,
        contents=contents,
        config={
            "response_mime_type": "application/json",
            "response_json_schema": schema,
        },
    )
    return response.text


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Input-Mode Pipelines
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def _build_extraction_prompt() -> str:
    """Insert current (or simulated) date into the prompt."""
    try:
        from dev_mode import get_current_date
        current = await get_current_date()
        current_date = current.strftime("%Y-%m-%d")
    except Exception:
        current_date = datetime.now().strftime("%Y-%m-%d")
    return EXTRACTION_PROMPT.replace("{current_date}", current_date)


async def extract_from_image(image_path: str) -> "ExtractionResult":
    """Mode 1 — Image input: receipt photo or shelf photo."""
    from google.genai import types
    from schemas import ExtractionResult

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    mime_type = mimetypes.guess_type(image_path)[0] or "image/jpeg"

    prompt = await _build_extraction_prompt()
    contents = [
        types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
        types.Part.from_text(text=prompt),
    ]

    raw = await call_gemini(contents, ExtractionResult.model_json_schema())
    return ExtractionResult.model_validate_json(raw)


async def extract_from_voice(audio_path: str) -> "ExtractionResult":
    """Mode 2 — Voice input: pre-recorded or live-captured audio."""
    from google.genai import types
    from schemas import ExtractionResult

    with open(audio_path, "rb") as f:
        audio_bytes = f.read()

    ext = audio_path.rsplit(".", 1)[-1].lower()
    mime_map = {
        "wav": "audio/wav",
        "mp3": "audio/mpeg",
        "aiff": "audio/aiff",
        "aac": "audio/aac",
        "ogg": "audio/ogg",
        "flac": "audio/flac",
    }
    mime_type = mime_map.get(ext, "audio/wav")

    prompt = await _build_extraction_prompt()
    contents = [
        types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
        types.Part.from_text(text=prompt),
    ]

    raw = await call_gemini(contents, ExtractionResult.model_json_schema())
    return ExtractionResult.model_validate_json(raw)


async def extract_from_text(text_input: str) -> "ExtractionResult":
    """Mode 3 — Text input: natural language string."""
    from pii_scrubber import scrub_pii
    from schemas import ExtractionResult

    scrubbed = scrub_pii(text_input)
    base_prompt = await _build_extraction_prompt()
    prompt = f"{base_prompt}\n\nUser input: {scrubbed}"

    raw = await call_gemini([prompt], ExtractionResult.model_json_schema())
    return ExtractionResult.model_validate_json(raw)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Fallback F2: Validation retry
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def call_gemini_with_validation_retry(
    contents: list[Any],
    max_retries: int = 1,
) -> "ExtractionResult":
    """
    F2: Call Gemini and validate. On ValidationError, retry ONCE
    with the error appended for self-correction.
    """
    import database as db
    from pydantic import ValidationError
    from schemas import ExtractionResult

    last_error = None
    raw_response = None

    for attempt in range(max_retries + 1):
        try:
            if attempt > 0 and last_error:
                from google.genai import types

                error_hint = types.Part.from_text(
                    text=f"\n\nYour previous response failed validation with this error: "
                    f"{last_error}\n\nPlease fix the output to match the schema exactly."
                )
                contents = contents + [error_hint]
                await db.log_audit(
                    "AI_RETRY",
                    severity="INFO",
                    details={"attempt": attempt + 1, "error": str(last_error)},
                )

            raw_response = await call_gemini(
                contents, ExtractionResult.model_json_schema()
            )
            result = ExtractionResult.model_validate_json(raw_response)
            return result

        except (ValidationError, ValueError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt >= max_retries:
                await db.insert_pending_review(
                    raw_input=str(contents)[:500],
                    llm_response=raw_response,
                    confidence_score=None,
                    failure_reason="VALIDATION_FAILED",
                )
                await db.log_audit(
                    "AI_FALLBACK",
                    severity="WARN",
                    details={
                        "reason": "VALIDATION_FAILED",
                        "attempts": attempt + 1,
                        "error": str(last_error),
                    },
                )
                raise

    raise RuntimeError("Unreachable")  # pragma: no cover


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Fallback F4: Rate-limit handling with exponential backoff
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def call_gemini_with_rate_limit_handling(
    contents: list[Any],
    schema: dict,
    notify_callback: Optional[Callable[[str], None]] = None,
    max_retries: int = 3,
) -> "ExtractionResult":
    """
    F4: Handle Gemini rate limits (HTTP 429) with exponential backoff.
    F4b: Handle network / auth errors gracefully.
    """
    import database as db
    from schemas import ExtractionResult

    try:
        raw = await call_gemini(contents, schema)
        return ExtractionResult.model_validate_json(raw)

    except Exception as first_exc:
        is_rate_limit = "ResourceExhausted" in type(first_exc).__name__ or "429" in str(
            first_exc
        )

        if not is_rate_limit:
            # F4b — non-rate-limit API error
            if notify_callback:
                notify_callback(
                    f"❌ API error: {type(first_exc).__name__}. "
                    f"Item routed to human review queue."
                )
            await db.log_audit(
                "AI_FALLBACK",
                severity="ERROR",
                details={"reason": "API_ERROR", "error": str(first_exc)},
            )
            raise

        # F4 — rate limit
        base_delay = 30
        for attempt in range(max_retries):
            delay = min(base_delay * (2**attempt), 120)
            if notify_callback:
                notify_callback(
                    f"⚠️  AI rate limit reached. Retrying in {delay}s "
                    f"(attempt {attempt + 1}/{max_retries})…"
                )
            await db.log_audit(
                "AI_RATE_LIMITED",
                severity="WARN",
                details={"retry_after_seconds": delay, "attempt": attempt + 1},
            )
            await asyncio.sleep(delay)

            try:
                raw = await call_gemini(contents, schema)
                if notify_callback:
                    notify_callback(
                        f"✅ Retry successful after {attempt + 1} attempt(s)."
                    )
                return ExtractionResult.model_validate_json(raw)
            except Exception as retry_exc:
                if attempt == max_retries - 1:
                    if notify_callback:
                        notify_callback(
                            f"❌ All {max_retries} retries failed. "
                            f"Item routed to human review queue."
                        )
                    await db.log_audit(
                        "AI_FALLBACK",
                        severity="ERROR",
                        details={
                            "reason": "RATE_LIMITED_RETRIES_EXHAUSTED",
                            "total_attempts": max_retries,
                        },
                    )
                    raise retry_exc
                continue

    raise RuntimeError("Unreachable")  # pragma: no cover


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Fallback F5: Empty response → retry then manual
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def handle_empty_response(
    original_contents: list[Any],
    input_method: str,
) -> "ExtractionResult":
    """
    F5: LLM returned zero items. Retry once with a rephrased prompt.
    If retry also empty → return an empty result so the caller can fall
    back to interactive manual entry.
    """
    import database as db
    from schemas import ExtractionResult

    try:
        from google.genai import types

        retry_prompt = types.Part.from_text(
            text="\n\nYour previous extraction returned zero items. "
            "Please look more carefully at the input. Even if the quality is poor, "
            "extract ANY items you can identify, even with low confidence scores."
        )
    except ImportError:
        retry_prompt = (
            "\n\nYour previous extraction returned zero items. "
            "Please look more carefully."
        )

    retry_contents = original_contents + [retry_prompt]

    await db.log_audit(
        "AI_RETRY",
        severity="INFO",
        details={"reason": "EMPTY_RESPONSE", "attempt": 2},
    )

    try:
        raw = await call_gemini(
            retry_contents, ExtractionResult.model_json_schema()
        )
        result = ExtractionResult.model_validate_json(raw)
        if result.items:
            await db.log_audit(
                "AI_RETRY_SUCCESS",
                severity="INFO",
                details={"items_found": len(result.items)},
            )
            return result
    except Exception:
        pass

    # All attempts returned empty
    await db.log_audit(
        "AI_FALLBACK",
        severity="WARN",
        details={"reason": "EMPTY_RESPONSE", "attempts": 2, "action": "MANUAL_ENTRY"},
    )
    return ExtractionResult(items=[], source_description="Empty — manual entry required")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Unified ingestion pipeline
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def process_input(
    input_data: str,
    input_method: str,
    notify_callback: Optional[Callable[[str], None]] = None,
    multiplier: float = 1.0,
) -> "IngestionResult":
    """
    Unified ingestion entry-point for all three input modes.
    Handles the full pipeline: extract → validate → normalise → route by confidence.
    """
    import database as db
    from carbon_lookup import lookup_carbon_impact
    from config import settings
    from normalizer import upsert_inventory_item
    from pii_scrubber import scrub_extracted_fields
    from schemas import ExtractionResult, IngestionResult

    result = IngestionResult()
    start = time.time()

    try:
        # ── Step 1: Extract ──────────────────────────────
        extraction: Optional[ExtractionResult] = None
        retry_count = 0

        try:
            async with asyncio.timeout(settings.llm_timeout_seconds):
                if input_method == "IMAGE":
                    extraction = await extract_from_image(input_data)
                elif input_method == "VOICE":
                    extraction = await extract_from_voice(input_data)
                elif input_method == "TEXT":
                    extraction = await extract_from_text(input_data)
                else:
                    raise ValueError(f"Unknown input method: {input_method}")

        except (TimeoutError, asyncio.TimeoutError):
            # F3 — Timeout → human review
            await db.insert_pending_review(
                raw_input=f"Timeout processing {input_method}: {input_data[:200]}",
                llm_response=None,
                confidence_score=None,
                failure_reason="TIMEOUT",
            )
            await db.log_audit(
                "AI_FALLBACK",
                severity="WARN",
                details={
                    "reason": "TIMEOUT",
                    "input_method": input_method,
                    "action": "ROUTED_TO_HUMAN_REVIEW",
                },
            )
            result.items_sent_to_review = 1
            result.review_reasons.append("TIMEOUT")
            result.fallback_triggered = "TIMEOUT"
            return result

        except (ValueError, Exception) as exc:
            # F2 / F4 / F4b — try validation retry or rate-limit handling
            is_validation = isinstance(exc, (ValueError,))
            if is_validation:
                try:
                    if input_method == "TEXT":
                        from pii_scrubber import scrub_pii

                        base_prompt = await _build_extraction_prompt()
                        contents = [
                            f"{base_prompt}\n\nUser input: {scrub_pii(input_data)}"
                        ]
                    elif input_method == "IMAGE":
                        from google.genai import types as gtypes
                        with open(input_data, "rb") as f:
                            img_bytes = f.read()
                        mime = mimetypes.guess_type(input_data)[0] or "image/jpeg"
                        prompt = await _build_extraction_prompt()
                        contents = [
                            gtypes.Part.from_bytes(data=img_bytes, mime_type=mime),
                            gtypes.Part.from_text(text=prompt),
                        ]
                    elif input_method == "VOICE":
                        from google.genai import types as gtypes
                        with open(input_data, "rb") as f:
                            aud_bytes = f.read()
                        ext = input_data.rsplit(".", 1)[-1].lower()
                        aud_mime = {"wav": "audio/wav", "mp3": "audio/mpeg"}.get(ext, "audio/wav")
                        prompt = await _build_extraction_prompt()
                        contents = [
                            gtypes.Part.from_bytes(data=aud_bytes, mime_type=aud_mime),
                            gtypes.Part.from_text(text=prompt),
                        ]
                    else:
                        contents = [input_data]
                    extraction = await call_gemini_with_validation_retry(
                        contents, max_retries=1
                    )
                    retry_count = 1
                except Exception:
                    result.items_sent_to_review = 1
                    result.review_reasons.append("VALIDATION_FAILED")
                    result.retry_count = 1
                    result.fallback_triggered = "VALIDATION_FAILED"
                    return result
            else:
                await db.insert_pending_review(
                    raw_input=f"API Error processing {input_method}: {input_data[:200]}",
                    llm_response=None,
                    confidence_score=None,
                    failure_reason="API_ERROR",
                )
                await db.log_audit(
                    "AI_FALLBACK",
                    severity="ERROR",
                    details={"reason": "API_ERROR", "error": str(exc)},
                )
                result.items_sent_to_review = 1
                result.review_reasons.append("API_ERROR")
                result.fallback_triggered = "API_ERROR"
                return result

        if extraction is None:
            return result

        # ── F5: Empty response check ─────────────────────
        if not extraction.items:
            extraction = await handle_empty_response(
                [input_data], input_method
            )
            retry_count = 1
            if not extraction.items:
                result.fallback_triggered = "EMPTY_RESPONSE"
                result.retry_count = retry_count
                return result

        # ── Apply quantity multiplier (image ingestion) ──
        if multiplier != 1.0:
            for item in extraction.items:
                item.quantity = round(item.quantity * multiplier, 4)
            logger.info("Applied multiplier %.2fx to %d items", multiplier, len(extraction.items))

        latency_ms = int((time.time() - start) * 1000)

        await db.log_audit(
            "AI_CALL",
            severity="INFO",
            input_method=input_method,
            model_used=settings.model_name,
            latency_ms=latency_ms,
            details={"items_extracted": len(extraction.items)},
        )

        # ── Step 2: Route items by confidence ─────────────
        for item in extraction.items:
            # PII scrub extracted fields before DB storage
            item_dict = item.model_dump()
            item_dict = scrub_extracted_fields(item_dict)

            if item.confidence_score < settings.confidence_threshold:
                # F1 — low confidence → pending review
                await db.insert_pending_review(
                    raw_input=item_dict.get("raw_input_text", str(item)),
                    llm_response=item.model_dump_json(),
                    confidence_score=item.confidence_score,
                    failure_reason="LOW_CONFIDENCE",
                    suggested_item_name=item.item_name,
                    suggested_quantity=item.quantity,
                )
                await db.log_audit(
                    "AI_FALLBACK",
                    severity="WARN",
                    confidence=item.confidence_score,
                    details={
                        "reason": "LOW_CONFIDENCE",
                        "score": item.confidence_score,
                        "item": item.item_name,
                    },
                )
                result.items_sent_to_review += 1
                result.review_reasons.append("LOW_CONFIDENCE")
            else:
                # Happy path → active inventory
                carbon = await lookup_carbon_impact(
                    item.item_name,
                    item.category.value if hasattr(item.category, "value") else item.category,
                    ai_client=_get_client(),
                    settings=settings,
                )

                # Back-fill expiry_date from carbon DB shelf life when AI left it null
                if not item.expiry_date:
                    from carbon_lookup import estimate_expiry_date
                    estimated_expiry = await estimate_expiry_date(item.item_name)
                    if estimated_expiry:
                        item.expiry_date = estimated_expiry

                upsert_result = await upsert_inventory_item(
                    item, carbon, input_method
                )
                result.items_added_to_inventory += 1
                result.total_carbon_footprint += carbon * item.quantity
                result.details.append(upsert_result)

                # Record an ADD event for forecasting
                try:
                    from dev_mode import get_current_date
                    now = await get_current_date()
                except Exception:
                    now = datetime.now()
                await db.insert_event(
                    item_id=upsert_result["item_id"],
                    timestamp=now.strftime("%Y-%m-%d %H:%M:%S"),
                    action_type="ADD",
                    qty_change=item.quantity,
                    day_of_week=now.weekday(),
                    is_weekend=1 if now.weekday() >= 5 else 0,
                    notes=f"Ingested via {input_method}",
                )

                await db.log_audit(
                    "INGESTION",
                    severity="INFO",
                    input_method=input_method,
                    confidence=item.confidence_score,
                    details={
                        "item": item.item_name,
                        "qty": item.quantity,
                        "action": upsert_result["action"],
                    },
                )

        result.retry_count = retry_count
        return result

    except Exception as exc:
        logger.exception("Unexpected error in process_input")
        await db.log_audit(
            "ERROR",
            severity="CRITICAL",
            details={"error": str(exc), "input_method": input_method},
        )
        raise


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Recipe generation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def generate_recipes_with_ai(
    expiring_items: list[dict],
) -> "RecipeResponse":
    """Generate recipes for expiring items using Gemini."""
    from schemas import RecipeResponse

    items_json = json.dumps(
        [
            {
                "name": item.get("item_name", "unknown"),
                "quantity": item.get("quantity", 0),
                "unit": item.get("unit", "units"),
                "expires_in_days": item.get("days_left", "?"),
            }
            for item in expiring_items
        ],
        indent=2,
    )
    prompt = RECIPE_PROMPT.format(expiring_items_json=items_json)
    raw = await call_gemini([prompt], RecipeResponse.model_json_schema())
    return RecipeResponse.model_validate_json(raw)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Triage (F3 timeout-guarded)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def triage_expiring_item(item_id: str) -> "TriageResult":
    """
    Attempt AI-powered triage with a 60-second timeout.
    F3: On timeout → route to human review (NO auto-discount).
    """
    import database as db
    from config import settings
    from schemas import TriageResult

    item = await db.get_item(item_id)
    if not item:
        return TriageResult(
            action_taken="NOT_FOUND",
            message=f"Item {item_id} not found",
        )

    try:
        async with asyncio.timeout(settings.llm_timeout_seconds):
            recipe_response = await generate_recipes_with_ai([item])

            # Persist recipes to DB
            for recipe in recipe_response.recipes:
                # CO2 saved = quantity diverted from waste × co2_per_unit
                co2_saved = 0.0
                for ingredient_name, qty_used in recipe.quantities_used.items():
                    for exp_item in [item]:
                        if ingredient_name.lower() in exp_item.get("item_name", "").lower() or exp_item.get("item_name", "").lower() in ingredient_name.lower():
                            co2_saved += exp_item.get("co2_per_unit_kg", 0) * qty_used
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

            await db.insert_triage_action(
                item_id=item_id,
                action_type="RECIPE_GENERATED",
                ai_generated=True,
                ai_bypassed=False,
                content=json.dumps([r.model_dump() for r in recipe_response.recipes]),
            )

            return TriageResult(
                action_taken="RECIPE_GENERATED",
                ai_generated=True,
                ai_bypassed=False,
                message=f"Generated {len(recipe_response.recipes)} recipe(s)",
                recipes=recipe_response.recipes,
            )

    except (TimeoutError, asyncio.TimeoutError):
        # F3 — NO auto-discount. Route to human review.
        await db.insert_pending_review(
            raw_input=f"Triage timeout for: {item['item_name']} (qty: {item['quantity']})",
            llm_response=None,
            confidence_score=None,
            failure_reason="TIMEOUT",
            suggested_item_name=item["item_name"],
            suggested_quantity=item["quantity"],
        )
        await db.log_audit(
            "AI_FALLBACK",
            severity="WARN",
            details={
                "reason": "TIMEOUT",
                "item_id": item_id,
                "action": "ROUTED_TO_HUMAN_REVIEW",
            },
        )
        return TriageResult(
            action_taken="PENDING_HUMAN_REVIEW",
            ai_generated=False,
            ai_bypassed=True,
            message="AI timed out after 60s. Item routed to human review queue.",
        )

    except Exception as exc:
        await db.log_audit(
            "AI_FALLBACK",
            severity="ERROR",
            details={
                "reason": "API_ERROR",
                "item_id": item_id,
                "error": str(exc),
            },
        )
        return TriageResult(
            action_taken="PENDING_HUMAN_REVIEW",
            ai_generated=False,
            ai_bypassed=True,
            message=f"AI error: {exc}. Item routed to human review queue.",
        )


def expiring_items_matching(
    items: list[dict], ingredient_names: list[str]
) -> list[dict]:
    """Helper to match recipe ingredients to expiring items."""
    matched = []
    for item in items:
        name = item.get("item_name", "").lower()
        for ingredient in ingredient_names:
            if ingredient.lower() in name or name in ingredient.lower():
                matched.append(item)
                break
    return matched


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Community Mesh (Stub / Mock)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def community_mesh_check(
    item_id: str, item_name: str, quantity: float
) -> dict:
    """
    STUB: Checks if any partner organisations need the expiring item.
    Mocks the check and logs the action. No real email sent.
    """
    import database as db

    partners = await db.get_partner_for_item(item_name)

    if partners:
        email_payload = {
            "to": partners[0]["email"],
            "subject": f"Available: {quantity} units of {item_name}",
            "body": (
                f"We have {quantity} units of {item_name} expiring soon. "
                f"Would your organisation like to receive this donation?"
            ),
        }
        await db.insert_triage_action(
            item_id=item_id,
            action_type="COMMUNITY_MESH",
            ai_generated=False,
            ai_bypassed=False,
            content=json.dumps(email_payload),
        )
        await db.log_audit(
            "COMMUNITY_MESH",
            details={
                "partner": partners[0]["name"],
                "item": item_name,
                "note": "MOCK — email not actually sent",
            },
        )
        return {"status": "DONATION_DRAFTED", "partner": partners[0]["name"]}

    return {"status": "NO_PARTNER_FOUND"}

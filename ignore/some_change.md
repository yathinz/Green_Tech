# Eco-Pulse V3.0 → V3.1 Changelog

All changes applied to `improved_idea.md` based on internal review.

---

## 1. Dev Mode Fixed for Grafana Compatibility
- **Removed** `days_until_expiry` GENERATED column from `inventory_items` table — SQLite GENERATED columns use the real `CURRENT_DATE`, not the Python-simulated date, breaking Dev Mode in Grafana.
- **Added** `system_config` table to persist `simulated_date` in the database, so both Python code and Grafana queries read the same simulated time.
- **Updated** all Grafana SQL queries to use `COALESCE((SELECT value FROM system_config WHERE key = 'simulated_date'), date('now'))` instead of `'now'`, so dashboards correctly reflect simulated time in Dev Mode.
- **Updated** `dev_mode.py` to persist the simulated date to `system_config` table instead of using an in-memory global variable (which Grafana can't access).

## 2. PII Scrubbing Clarified — Text-Only Pre-AI + All-Data Pre-DB
- **Pre-AI scrubbing:** Applied to **text input only**. Image and voice media is sent directly to Gemini — it is the user's responsibility to not photograph sensitive documents.
- **Pre-DB scrubbing:** ALL extracted data (from any input mode) is PII-scrubbed before database storage, ensuring no PII persists in the system regardless of input method.
- **Architecture diagram** updated to show two scrubbing stages.
- **Tradeoff 1** updated to accurately describe the approach instead of claiming "before ANY data leaves the local environment."

## 3. Test File Naming Consistency
- **Standardized** to `test_timeout_and_ratelimit.py` everywhere (was `test_timeout_heuristics.py` in the repo structure).

## 4. Unit Description Fixed — No "packs" in DB
- **Updated** `inventory_items.unit` description from `(kg, L, units, packs)` to `(kg, g, L, mL, units)` — matching the `ItemUnit` enum. The normalizer pipeline guarantees packs never reach the database.
- **Updated** CLI output example to show `units` instead of `packs` for the mystery item.

## 5. PII Scrubber Made Synchronous
- `scrub_pii()` and `scrub_extracted_fields()` are now **synchronous** functions — PII redaction is a pure regex operation with no I/O, so async is unnecessary and was causing a sync→async call conflict with `log_audit()`.
- Uses a sync `_sync_log_pii_event()` helper instead of calling async `log_audit()`.

## 6. Weekend Multiplier NaN Guard
- **Added** guard for when dataset has no weekend entries: `if not weekend_values: weekend_multiplier = 1.0`. Previously, `np.mean([])` would produce `NaN` and crash downstream calculations.

## 7. `convert_to_target_unit()` — Implementation Plan Added
- **Added** function description and specification in the normalizer section. Converts between compatible unit families (g↔kg, mL↔L) for quantity merging during deduplication.

## 8. SQLite PRAGMA Fixed to Async
- **Updated** PRAGMA setup from sync `cursor.execute()` to async `await connection.execute()` — matching the async `aiosqlite` tech stack.

## 9. Forecast Scheduler — Implementation Plan Added
- **Added** specification for an `asyncio` periodic task launched in FastAPI's startup event to run forecasts every hour. Replaces the vague "cron job" mention with a concrete implementation plan.

## 10. Carbon CSV Data Normalized
- **All item names** in `carbon_impact_db.csv` converted to lowercase singular form (e.g., `"Whole Milk"` → `"whole milk"`, `"Organic Apples"` → `"organic apple"`) to match the normalizer pipeline output.

## 11. Data Fixes — Eggs, Category Misclassifications
- **`Eggs (dozen)`** → `"egg"` with `co2_per_unit_kg = 0.35` (per unit, not per dozen).
- **`Napkins (pack)`** → `"napkin"`, **`Sugar (kg)`** → `"sugar"`.
- **White Rice, Pasta, Olive Oil, Sugar** moved from `"Produce"` to proper granular categories.
- **Coffee Beans, Orange Juice, Oat Milk** moved from generic `"Beverages"` to specific sub-categories.

## 12. Granular Item Categories
- **Replaced** the 9 broad categories (`Dairy`, `Produce`, `Meat`, etc.) with **30 specific categories** maintaining consistent granularity:
  - Dairy split into: Milk & Cream, Cheese, Yogurt, Butter & Spreads, Eggs
  - Produce split into: Fresh Fruit, Fresh Vegetables, Herbs & Leafy Greens, Root Vegetables
  - Meat split into: Poultry, Red Meat, Seafood
  - Bakery split into: Bread & Rolls, Pastry & Cakes
  - Added: Grains & Rice, Pasta & Noodles, Cooking Oils & Vinegar, Condiments & Sauces, Sugar & Sweeteners, Nuts & Seeds, Canned & Preserved, Coffee & Tea, Juice & Soft Drinks, Plant-Based Milk
  - Non-food: Office - Paper, Office - Supplies, Cleaning Products, Lab Chemicals, Lab Equipment, Other
- **Updated** extraction prompt, carbon CSV, and test data to use new categories.

## 13. Recipe `ingredients_used` — Consistent `list[str]` of Names
- **Standardized** the `recipes` table `ingredients_used` column to store a JSON array of ingredient **names** (not item_ids), matching the `RecipeResponse` Pydantic schema.

## 14. Database Indexes — Implementation Plan Added
- **Added** index specifications for performance-critical queries:
  - `inventory_items(status, expiry_date)` — triage queries
  - `inventory_events(item_id, timestamp)` — forecast queries
  - `audit_log(event_type, timestamp)` — dashboard panels
  - `pending_human_review(reviewed)` — review queue

## 15. Voice Input `--file` Flag for Docker
- **Added** `--file` option to `eco-pulse ingest --voice` for Docker/demo mode where microphone hardware is unavailable.
- Auto-detects lack of audio hardware and prompts for a file path.

## 16. Exponential Backoff for Rate Limits
- **Upgraded** F4 rate limit handling from single fixed retry to exponential backoff with up to 3 retries: `delay = min(base_delay * 2^attempt, 120)`.

## 18. `conftest.py` — Full Specification Added
- **Defined** shared test fixtures: in-memory SQLite database, mock Gemini client, sample extraction results, test settings, and seeded database fixture.

## 19. Docker Compose `version` Key Removed
- **Removed** deprecated `version: "3.8"` from `docker-compose.yml`.

## 21. Graceful `GEMINI_API_KEY` Validation
- **Added** startup validator in `config.py` that prints a clear error message with instructions if the API key is missing or still using the placeholder value.

## 22. Demo Fallback Commands — Planning Added
- **Added** `dev force-timeout` and `dev simulate-rate-limit` to CLI command structure and implementation checklist for demonstrating fallback paths during the video demo.

---

*Changes applied: March 19, 2026 | Version: 3.1*

fix if I already have milk and buy more milk with a different expiry date, it should create a different entry
go through the code base and make item+expiry date the key for checking if item already exists

Now let me check if there are other places using Part.from_text() with a positional argument:


In the newer google-genai SDK, Part.from_text() requires text= as a keyword argument. Let me fix all 6 occurrences:

Edited
ai_service.py+6-6
Fixed all 6 Part.from_text() calls to use the text= keyword argument. The newer google-genai SDK requires it as a keyword-only parameter. Rebuild the container to pick up the fix.
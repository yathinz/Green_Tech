1) dev mode was broken for grafana because the days_until_expiry generated column in inventory_items used sqlite's real current_date instead of the python-simulated date. removed that column entirely, added a system_config table to persist simulated_date in the db, and updated all grafana sql queries to read from that table so dashboards respect simulated time. also updated dev_mode.py to write the simulated date to system_config instead of holding it in a python variable that grafana can't see.

2) clarified how pii scrubbing works. pre-ai scrubbing only applies to text input since images and voice go straight to gemini. pre-db scrubbing applies to all extracted data regardless of input mode so nothing with pii ends up in the database. updated the architecture diagram and tradeoff 1 to reflect this accurately.

3) standardized test file naming. test_timeout_heuristics.py was renamed to test_timeout_and_ratelimit.py everywhere to stay consistent.

4) fixed the unit description on inventory_items from (kg, L, units, packs) to (kg, g, L, mL, units) to match the ItemUnit enum. the normalizer already guarantees packs never reach the db. updated the cli output example accordingly.

5) made scrub_pii() and scrub_extracted_fields() synchronous. pii redaction is pure regex with no i/o so async was unnecessary and was causing a sync-to-async conflict when calling log_audit(). added a sync _sync_log_pii_event() helper instead.

6) added a nan guard for the weekend multiplier. if the dataset has no weekend entries np.mean([]) would return nan and crash downstream. now it defaults to 1.0 in that case.

7) added convert_to_target_unit() to the normalizer. converts between compatible unit families (g to kg, ml to l) for merging quantities during deduplication.

8) fixed sqlite pragma setup to use async await connection.execute() instead of sync cursor.execute() to match the aiosqlite stack.

9) added a forecast scheduler spec. an asyncio periodic task launches at fastapi startup and runs forecasts every hour. replaces the vague cron job mention with a concrete plan.

10) normalized all item names in carbon_impact_db.csv to lowercase singular form (whole milk instead of Whole Milk, organic apple instead of Organic Apples) so they match the normalizer pipeline output.

11) fixed data issues with eggs, napkins, sugar, and several category misclassifications. eggs changed from per-dozen to per-unit pricing, white rice and pasta moved out of produce into proper categories, coffee beans and orange juice moved into their specific beverage sub-categories.

12) replaced the 9 broad categories with 30 granular ones. dairy split into milk & cream, cheese, yogurt, butter & spreads, eggs. produce split into fresh fruit, fresh vegetables, herbs & leafy greens, root vegetables. meat split into poultry, red meat, seafood. bakery split into bread & rolls, pastry & cakes. added grains & rice, pasta & noodles, cooking oils & vinegar, condiments & sauces, sugar & sweeteners, nuts & seeds, canned & preserved, coffee & tea, juice & soft drinks, plant-based milk, and six non-food categories. updated the extraction prompt, carbon csv, and test data to use them.

13) standardized recipe ingredients_used to store a json array of ingredient names instead of item ids, matching the pydantic schema.

14) added database indexes for the hot query paths. inventory_items on status and expiry_date for triage, inventory_events on item_id and timestamp for forecasts, audit_log on event_type and timestamp for dashboards, and pending_human_review on reviewed for the review queue.

15) added a --file flag to voice ingestion for docker and demo mode where there's no microphone hardware. auto-detects missing audio hardware and prompts for a file path.

16) upgraded rate limit handling from a single fixed retry to exponential backoff with up to 3 retries capped at 120 seconds.

17) defined all shared test fixtures in conftest.py. in-memory sqlite database, mock gemini client, sample extraction results, test settings, and a seeded database fixture.

18) removed the deprecated version 3.8 key from docker-compose.yml.

19) added graceful gemini api key validation at startup. config.py now prints a clear error with instructions if the key is missing or still set to the placeholder value.

20) added dev force-timeout and dev simulate-rate-limit cli commands for demonstrating fallback paths during the video demo.

21) fixed item deduplication to use item name plus expiry date as the composite key. buying milk with a different expiry date now creates a separate inventory entry instead of merging into the existing one.

22) fixed all 6 Part.from_text() calls in ai_service.py to use the text= keyword argument. the newer google-genai sdk requires it as keyword-only.

23) csv import now looks up co2_per_unit_kg from the carbon db when the csv doesn't provide it instead of defaulting to 0. also estimates expiry_date from avg_shelf_life_days when expiry is missing.

24) improved carbon db fuzzy matching with token and substring fallback so items like penne pasta match the pasta entry and chopped tomato matches tomato. the old 0.85 threshold alone couldn't handle qualified names.

25) ai ingestion now backfills expiry_date from the carbon db shelf life data when gemini returns null for expiry on a perishable item.

26) implemented community mesh donation partner matching. added get_all_partners(), find_donation_matches(), and record_donation() to database.py. find_donation_matches joins inventory with the carbon db, sorts by fefo, and filters by preferred partner. record_donation updates the item status to DONATED, logs an inventory event, creates a COMMUNITY_MESH triage action with a mock email payload, and audits the co2 saved. added three api endpoints (/community-mesh/partners, /matches, /donate/{id}) and a community-mesh cli subcommand. added 5 new tests covering partner listing, match finding, N/A exclusion, full donation flow with co2 calculation, and item-not-found error handling. total tests now 37 across 7 files.

27) fixed the waste prevention score showing 0 after seeding. the seed data was creating all inventory items with status ACTIVE so the grafana query counting CONSUMED/DONATED rows found nothing. added historical completed items (consumed, donated, expired batches) to the seeder with their actual quantities preserved as source of truth. those amounts are deducted from the corresponding active items so active stock levels reflect reality. updated the inventory overview panel to show consumed and donated items at the bottom with a ✅ urgency tag, sorted after active items. rewrote the waste prevention score query to include burn-rate predictions — it now counts historically saved items (CONSUMED + DONATED) plus active items predicted to be consumed before expiry by joining the forecasts table and comparing predicted_runout_date against expiry_date. scoped the co2 saved panel to DONATED items only since consumed items were used, not diverted from waste.
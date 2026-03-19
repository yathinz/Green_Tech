# 🌍 Eco-Pulse V3.0: The Zero-Waste Inventory Engine — Definitive Implementation Blueprint

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Model Selection & Justification](#2-model-selection--justification)
3. [Architecture & Tech Stack](#3-architecture--tech-stack)
4. [Database Design — Complete Schema](#4-database-design--complete-schema)
5. [CLI Interface Design (Primary Demo Surface)](#5-cli-interface-design-primary-demo-surface)
6. [API Design — All Endpoints](#6-api-design--all-endpoints)
7. [AI Integration — All Three Input Modes](#7-ai-integration--all-three-input-modes)
7b. [Input Standardization & Deduplication Pipeline](#7b-input-standardization--deduplication-pipeline)
8. [Fallback Engineering — Complete Matrix](#8-fallback-engineering--complete-matrix)
9. [Predictive Analytics — Upgraded Regression](#9-predictive-analytics--upgraded-regression)
10. [Grafana Dashboard Specification](#10-grafana-dashboard-specification)
11. [Synthetic Datasets](#11-synthetic-datasets)
12. [Docker Setup](#12-docker-setup)
13. [Testing Strategy — Comprehensive](#13-testing-strategy--comprehensive)
14. [Developer Mode — Time Simulation](#14-developer-mode--time-simulation)
15. [Repository Structure](#15-repository-structure)
16. [PII Scrubber](#16-pii-scrubber)
17. [Configuration Management](#17-configuration-management)
18. [Tradeoffs Documentation](#18-tradeoffs-documentation)
19. [Video Script (Updated)](#19-video-script-updated)
20. [End-to-End Demo Flows](#20-end-to-end-demo-flows)
21. [Implementation Checklist](#21-implementation-checklist)

---

## 1. Executive Summary

### The Problem
Small businesses (cafes), non-profits, and university labs lack the time for manual inventory entry and the analytics to prevent perishable waste. This leads to massive financial loss and a hidden, high carbon footprint. Existing tools are either dumb spreadsheets or bloated enterprise ERPs.

### The Solution
A fully Dockerized, CLI-first, AI-powered inventory lifecycle manager that runs with a single `docker compose up` command. Two containers. Zero frontend code. Full Grafana dashboards.

### The Three Scoring Pillars — How We Maximise Each

| Scoring Metric | How Eco-Pulse Wins |
|---|---|
| **🗑️ Waste Reduction** | FEFO-ordered triage, burn-rate forecasting with day-of-week seasonality, AI-generated recipes for expiring goods, carbon impact tracking, proactive alerts |
| **⚡ Ease of Entry** | Three frictionless input modes (📷 image, 🎙️ voice, ✏️ text) — all via a single CLI command. No forms, no manual typing. Natural language → structured data in seconds |
| **🤖 AI Application** | Gemini 2.5 Flash for multimodal extraction + recipe generation. Deterministic math for forecasting. **5 distinct fallback paths** for when AI fails: low confidence routing, timeout heuristics, Pydantic validation rejection, API failure graceful degradation, and rule-based manual entry |

### What Changed from V2.0 (Changes i made from LLM implementation)

| Area | V2.0 (Initial Idea) | V3.0 (This Document) |
|---|---|---|
| AI Model | Gemini 1.5 Flash (deprecated) | **Gemini 2.5 Flash** (stable, free, multimodal including audio) |
| Database | PostgreSQL (separate container) | **SQLite** (embedded, zero-config, shared volume to Grafana) |
| Interface | Swagger UI / Postman | **Typer + Rich CLI** (beautiful terminal output, demo-ready) |
| Voice Input | Mentioned but unplanned | **Fully implemented** via Gemini audio understanding |
| Grafana Connection | Via Prometheus | **Direct SQLite plugin** (`frser-sqlite-datasource`) |
| Docker Services | 4 containers | **2 containers** (app + grafana) |
| Linear Regression | Basic 14-day window | **Day-of-week features**, weekend/weekday splits, seasonal clusters |
| Triage Ordering | Unspecified | **FEFO** (First Expired First Out) |
| Fallback Paths | 2 (low confidence, timeout) | **5 comprehensive fallback paths** |
| Community Mesh | Full implementation | **Stub/mock** (shows concept, logs action, no real email) |
| Grafana Panels | 3 conceptual | **10 fully specified panels** with SQL queries |
| Tests | 3 test files | **6+ test files** covering all fallback paths |
| Dev Mode | Not planned | **Time simulation** via `--dev-mode` flag |
| Config Management | Not addressed | **pydantic-settings** with `.env` support |
| PII Scrubber | Conceptual | **Regex middleware** implementation spec |

---

## 2. Model Selection & Justification

### Winner: **Gemini 2.5 Flash** (`gemini-2.5-flash`)

| Factor | Details |
|---|---|
| **Free Tier** | ✅ Completely free — text, image, video, and audio input |
| **Multimodal** | ✅ Text + Image + Audio + Video — one model handles ALL our input modes |
| **Structured Output** | ✅ Native `response_json_schema` with Pydantic `model_json_schema()` support |
| **Stability** | ✅ Stable release (not preview) — won't change under us |
| **Context Window** | 1M tokens — handles long audio, multiple images, large prompts |
| **Reasoning** | Hybrid reasoning model with configurable thinking budgets |
| **Deprecation Risk** | None — Gemini 2.0 Flash is deprecated (June 2026 shutdown), but 2.5 Flash is current |
| **Rate Limits (Free)** | Generous for <100 req/day usage |
| **Audio Support** | Native — WAV, MP3, AIFF, AAC, OGG, FLAC. 32 tokens/second. Up to 9.5 hours |
| **SDK** | `google-genai` Python SDK (official, well-documented) |

### Why Not Others?

| Model | Reason Rejected |
|---|---|
| Gemini 2.0 Flash | **Deprecated** — shutting down June 1, 2026 |
| Gemini 3 Flash Preview | Preview = may change without notice. Not suitable for stable demo |
| Gemini 3.1 Flash-Lite Preview | Preview, and no free standard tier (free input only, no free output) |
| Gemini 2.5 Pro | Free but overkill for extraction tasks; slower |
| OpenAI GPT-4o | Not free; requires paid API key |
| Claude | Not free; no native multimodal audio |
| Llama local | Hardware constraints, no native structured output, Docker image bloat |

### Upgrade Path
If Gemini 3 Flash becomes stable during development, we can swap models with a single config change (`MODEL_NAME` env var). The Pydantic schemas and prompts remain identical.

---

## 3. Architecture & Tech Stack

### The 2-Container Dockerized Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                        docker compose up                           │
├───────────────────────────────────┬────────────────────────────────┤
│         Container 1: app          │       Container 2: grafana     │
│                                   │                                │
│  ┌─────────────────────────┐      │   ┌────────────────────────┐  │
│  │   FastAPI (Port 8000)   │      │   │  Grafana (Port 3000)   │  │
│  │   + Typer CLI           │      │   │  + SQLite Plugin       │  │
│  │   + SQLite (WAL mode)   │      │   │  + Auto-provisioned    │  │
│  │   + scikit-learn        │      │   │    dashboards           │  │
│  │   + Gemini 2.5 Flash    │      │   └─────────┬──────────────┘  │
│  └─────────────┬───────────┘      │             │                  │
│                │                  │             │                  │
│         ┌──────▼──────┐           │      ┌──────▼──────┐          │
│         │ ecopulse.db │◄──────────┼──────┤ READ-ONLY   │          │
│         │  (SQLite)   │  shared   │      │  access     │          │
│         └─────────────┘  volume   │      └─────────────┘          │
└───────────────────────────────────┴────────────────────────────────┘
```

### Tech Stack — Final

| Layer | Technology | Justification |
|---|---|---|
| **Backend API** | Python 3.12 + FastAPI | Async native, BackgroundTasks, Pydantic integration, OpenAPI docs |
| **CLI Interface** | Typer + Rich | Type-hinted CLI (same philosophy as FastAPI), beautiful terminal tables/panels |
| **Data Validation** | Pydantic v2 | Strict JSON schemas, `model_json_schema()` for Gemini structured output |
| **Database** | SQLite 3 (WAL mode) | Zero-config, no container, file-based, shared volume to Grafana |
| **Async DB** | `aiosqlite` + SQLAlchemy async | Non-blocking DB operations in async FastAPI context |
| **AI Layer** | Gemini 2.5 Flash via `google-genai` SDK | Free, multimodal (text+image+audio), structured output |
| **Forecasting** | scikit-learn `LinearRegression` | Deterministic, fast, day-of-week features |
| **Dashboards** | Grafana OSS + `frser-sqlite-datasource` plugin | Zero-frontend, auto-provisioned, reads SQLite directly |
| **Config** | pydantic-settings + `.env` | Type-safe env var management |
| **Testing** | pytest + pytest-asyncio + unittest.mock | Async test support, AI mock patterns |
| **Containerization** | Docker + Docker Compose | Single command deployment |
| **Audio Recording** | `sounddevice` + `soundfile` (CLI only) | Cross-platform audio capture for voice input |

---

## 4. Database Design — Complete Schema

### Engine: SQLite 3 with WAL (Write-Ahead Logging) Mode

WAL mode enables concurrent reads (Grafana) while the app writes. Set on connection:
```python
# On every connection (async via aiosqlite)
await connection.execute("PRAGMA journal_mode=WAL;")
await connection.execute("PRAGMA busy_timeout=5000;")
```

### Table: `inventory_items` (Core Inventory)

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | TEXT | PK, UUID4 | Unique item identifier |
| `item_name` | TEXT | NOT NULL | Name of the item |
| `category` | TEXT | NOT NULL | Granular category (Milk & Cream, Cheese, Fresh Fruit, Poultry, etc.) |
| `quantity` | REAL | NOT NULL, >= 0 | Current quantity |
| `unit` | TEXT | NOT NULL | Unit of measurement (kg, g, L, mL, units) |
| `expiry_date` | TEXT | ISO 8601 date | Expiration date (nullable for non-perishables) |
| `status` | TEXT | NOT NULL, DEFAULT 'ACTIVE' | ACTIVE, EXPIRING_SOON, EXPIRED, PENDING_TRIAGE, DONATED, CONSUMED |
| `co2_per_unit_kg` | REAL | DEFAULT 0.0 | Carbon impact per unit (from Green DB lookup, or AI-estimated for unknown items) |
| `confidence_score` | REAL | CHECK(0..1) | LLM confidence when item was ingested |
| `input_method` | TEXT | NOT NULL | IMAGE, VOICE, TEXT, MANUAL, CSV_IMPORT |
| `created_at` | TEXT | DEFAULT CURRENT_TIMESTAMP | When the item was added |
| `updated_at` | TEXT | DEFAULT CURRENT_TIMESTAMP | Last modification timestamp |

### Table: `pending_human_review` (Fallback Queue)

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | TEXT | PK, UUID4 | Unique review ID |
| `raw_input` | TEXT | NOT NULL | Original input (text, image path, audio path) |
| `llm_response` | TEXT | | Raw LLM response JSON |
| `confidence_score` | REAL | | The low confidence score that triggered review |
| `failure_reason` | TEXT | NOT NULL | LOW_CONFIDENCE, VALIDATION_FAILED, API_ERROR, TIMEOUT |
| `suggested_item_name` | TEXT | | LLM's best guess for item name |
| `suggested_quantity` | REAL | | LLM's best guess for quantity |
| `reviewed` | INTEGER | DEFAULT 0 | 0 = pending, 1 = approved, 2 = rejected |
| `created_at` | TEXT | DEFAULT CURRENT_TIMESTAMP | When flagged |

### Table: `inventory_events` (Time-Series Usage Data)

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | INTEGER | PK, AUTOINCREMENT | Event ID |
| `item_id` | TEXT | FK → inventory_items.id | Which item was affected |
| `timestamp` | TEXT | NOT NULL, ISO 8601 | When the event occurred |
| `action_type` | TEXT | NOT NULL | ADD, USE, RESTOCK, WASTE, DONATE, ADJUST |
| `qty_change` | REAL | NOT NULL | Positive for add, negative for use |
| `day_of_week` | INTEGER | 0-6 (Mon-Sun) | Extracted for regression features |
| `is_weekend` | INTEGER | 0 or 1 | Weekend flag for regression |
| `notes` | TEXT | | Human-readable note (e.g., "Morning rush") |

### Table: `carbon_impact_db` (Green DB Lookup)

| Column | Type | Constraints | Description |
|---|---|---|---|
| `item_id` | TEXT | PK | Lookup key |
| `item_name` | TEXT | NOT NULL, UNIQUE | Canonical item name |
| `category` | TEXT | NOT NULL | Dairy, Produce, Meat, Bakery, Office, Chemical, etc. |
| `co2_per_unit_kg` | REAL | NOT NULL | kg CO₂ per unit |
| `avg_shelf_life_days` | INTEGER | | Average shelf life in days |
| `preferred_partner` | TEXT | DEFAULT 'N/A' | Preferred donation partner |

### Table: `triage_actions` (Circular Economy Actions)

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | TEXT | PK, UUID4 | Action ID |
| `item_id` | TEXT | FK → inventory_items.id | Which item triggered triage |
| `action_type` | TEXT | NOT NULL | RECIPE_GENERATED, COMMUNITY_MESH, AUTO_DISCOUNT, DONATION_DRAFTED |
| `ai_generated` | INTEGER | NOT NULL | 1 = AI generated, 0 = rule-based fallback |
| `ai_bypassed` | INTEGER | DEFAULT 0 | 1 = AI was unavailable/failed |
| `content` | TEXT | | The recipe text, email draft, or action description |
| `created_at` | TEXT | DEFAULT CURRENT_TIMESTAMP | When the action was taken |

### Table: `audit_log` (System Audit Trail)

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | INTEGER | PK, AUTOINCREMENT | Log ID |
| `timestamp` | TEXT | DEFAULT CURRENT_TIMESTAMP | When the event occurred |
| `event_type` | TEXT | NOT NULL | AI_CALL, AI_FALLBACK, AI_BYPASSED, INGESTION, TRIAGE, FORECAST, ERROR, PII_SCRUBBED |
| `severity` | TEXT | DEFAULT 'INFO' | INFO, WARN, ERROR, CRITICAL |
| `details` | TEXT | | JSON blob with event-specific data |
| `input_method` | TEXT | | IMAGE, VOICE, TEXT (if applicable) |
| `model_used` | TEXT | | Which AI model was called |
| `latency_ms` | INTEGER | | API call latency in milliseconds |
| `confidence` | REAL | | Confidence score (if applicable) |

### Table: `forecasts` (Cached Predictions)

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | INTEGER | PK, AUTOINCREMENT | Forecast ID |
| `item_id` | TEXT | FK → inventory_items.id | Which item |
| `predicted_runout_date` | TEXT | | Predicted date of stock depletion |
| `days_of_supply` | REAL | | Estimated days of supply remaining |
| `daily_burn_rate` | REAL | | Average units consumed per day |
| `r_squared` | REAL | | Model fit quality (0.0-1.0) |
| `data_points_used` | INTEGER | | Number of historical events used |
| `computed_at` | TEXT | DEFAULT CURRENT_TIMESTAMP | When this forecast was generated |

### Table: `recipes` (AI-Generated Recipes for Grafana)

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | TEXT | PK, UUID4 | Recipe ID |
| `title` | TEXT | NOT NULL | Recipe name |
| `ingredients_used` | TEXT | NOT NULL | JSON array of ingredient names used |
| `ingredient_names` | TEXT | NOT NULL | Comma-separated item names (for Grafana display) |
| `instructions` | TEXT | NOT NULL | Recipe steps |
| `estimated_servings` | INTEGER | | Number of servings |
| `co2_saved_kg` | REAL | | CO₂ saved by using these ingredients instead of wasting |
| `ai_generated` | INTEGER | DEFAULT 1 | 1 = AI, 0 = rule-based fallback |
| `created_at` | TEXT | DEFAULT CURRENT_TIMESTAMP | When generated |

### Table: `system_config` (Dev Mode & System Settings)

| Column | Type | Constraints | Description |
|---|---|---|---|
| `key` | TEXT | PK | Configuration key (e.g., 'simulated_date') |
| `value` | TEXT | NOT NULL | Configuration value |
| `updated_at` | TEXT | DEFAULT CURRENT_TIMESTAMP | When last updated |

> **Why this table?** Dev Mode stores the simulated date here so that **both** Python code and Grafana SQL queries read the same simulated time. An in-memory variable would only affect the Python app — Grafana would still use real `'now'`, breaking dashboard consistency.

### Database Indexes (Performance)

The following indexes should be created at database initialization for Grafana and query performance:

```sql
-- Triage queries: filter by status + sort by expiry
CREATE INDEX idx_inventory_status_expiry ON inventory_items(status, expiry_date);

-- Forecast queries: filter usage events by item + time range
CREATE INDEX idx_events_item_timestamp ON inventory_events(item_id, timestamp);

-- Dashboard panels: filter audit log by event type + time
CREATE INDEX idx_audit_event_timestamp ON audit_log(event_type, timestamp);

-- Review queue: filter by review status
CREATE INDEX idx_review_status ON pending_human_review(reviewed);

-- Carbon lookup: fuzzy match by item name
CREATE INDEX idx_carbon_item_name ON carbon_impact_db(item_name);

-- Forecast cache: lookup by item
CREATE INDEX idx_forecast_item ON forecasts(item_id);
```

---

## 5. CLI Interface Design (Primary Demo Surface)

### Stack: Typer + Rich

Both are from the FastAPI ecosystem. Typer handles argument parsing with Python type hints. Rich provides beautiful terminal output with tables, panels, progress bars, and color.

### Command Structure

```
eco-pulse
├── ingest          # Add items to inventory
│   ├── --image     # Upload a receipt/shelf photo
│   ├── --voice     # Record audio (or use --file for pre-recorded audio in Docker)
│   ├── --text      # Natural language text input
│   └── --csv       # Bulk import from CSV
│
├── inventory       # View and manage inventory
│   ├── list        # List all items (with filters)
│   ├── search      # Search by name/category
│   ├── update      # Update an item's quantity
│   └── review      # View & approve pending items
│
├── triage          # Expiring items actions
│   ├── (default)   # Show FEFO-ordered expiring items + trigger AI recipes
│   └── --dry-run   # Preview actions without DB writes
│
├── forecast        # Burn-rate predictions
│   ├── (default)   # Forecast all items
│   └── --item-id   # Forecast specific item
│
├── dashboard       # Open Grafana
│   └── (default)   # Opens browser to localhost:3000
│
├── dev             # Developer mode
│   ├── advance-time --days N   # Simulate time passing
│   ├── seed-data               # Load synthetic data
│   ├── reset-db                # Reset database
│   ├── force-timeout           # Force AI timeout to demo F3 fallback
│   └── simulate-rate-limit     # Rapid-fire AI calls to demo F4 fallback
│
└── health          # System health check
```

### CLI Output Examples

#### `eco-pulse ingest --image receipt.jpg`
```
╭──── 🧾 Receipt Processing ─────────────────────────────╮
│ Input:    receipt.jpg (IMAGE)                            │
│ Model:    gemini-2.5-flash                              │
│ Status:   ✅ Processing Complete                        │
│ Latency:  1,243ms                                       │
╰─────────────────────────────────────────────────────────╯

 Extracted Items:
┏━━━━━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
┃ Item             ┃ Qty  ┃ Unit  ┃ Expiry      ┃ Confidence ┃ CO₂/unit (kg)  ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
│ Whole Milk       │ 10   │ L     │ 2026-03-25  │ 94%  ✅    │ 3.2            │
│ Organic Apples   │ 50   │ units │ 2026-03-28  │ 91%  ✅    │ 0.4            │
│ Cheddar Cheese   │ 2    │ kg    │ 2026-04-15  │ 88%  ✅    │ 13.5           │
│ ⚠️ Mystery Item  │ 5    │ units │ ???         │ 62%  ⚠️    │ —              │
└──────────────────┴──────┴───────┴─────────────┴────────────┴────────────────┘

 ⚠️  1 item routed to PENDING_HUMAN_REVIEW (confidence < 85%)
 ✅  3 items added to active inventory
 🌍  Total carbon footprint: 59.0 kg CO₂
```

#### `eco-pulse triage`
```
╭──── 🚨 Expiry Triage (FEFO Order) ─────────────────────╮
│ Items Expiring Within 7 Days: 4                         │
│ Items Expiring Within 3 Days: 2  ← AI TRIAGE TRIGGERED │
╰─────────────────────────────────────────────────────────╯

┏━━━━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Item            ┃ Qty  ┃ Expires     ┃ Status  ┃ Action Taken              ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 🔴 Whole Milk   │ 8 L  │ Tomorrow    │ URGENT  │ 🍳 Recipe: Milk Pudding   │
│ 🔴 Yogurt       │ 5 ct │ 2 days      │ URGENT  │ 🍳 Recipe: Smoothie Bowl  │
│ 🟡 Apples       │ 30   │ 5 days      │ WARNING │ Monitoring                │
│ 🟡 Bread        │ 4    │ 6 days      │ WARNING │ Monitoring                │
└─────────────────┴──────┴─────────────┴─────────┴───────────────────────────┘

╭──── 🍳 AI-Generated "Save-It" Recipes ─────────────────╮
│                                                         │
│ 1. 🥄 Creamy Milk Pudding (uses 3L Whole Milk)         │
│    Servings: 6 | CO₂ Saved: 9.6 kg                     │
│    Steps: Heat milk, add sugar and cornstarch...        │
│                                                         │
│ 2. 🥤 Berry Smoothie Bowl (uses 3 Yogurt, 5 Apples)   │
│    Servings: 4 | CO₂ Saved: 5.8 kg                     │
│    Steps: Blend yogurt with frozen berries...           │
│                                                         │
╰─────────────────────────────────────────────────────────╯
```

#### `eco-pulse forecast --item-id <id>`
```
╭──── 📈 Burn-Rate Forecast: Whole Milk ──────────────────╮
│ Current Stock:       8 L                                │
│ Daily Burn Rate:     2.1 L/day                          │
│ Weekend Multiplier:  1.6x                               │
│ Days of Supply:      3.2 days                           │
│ Predicted Run-Out:   2026-03-22 (Saturday)              │
│ Model R²:            0.87                               │
│ Data Points Used:    14                                  │
│                                                         │
│ ⚠️  REORDER RECOMMENDED — Will run out before next      │
│     delivery window (Monday)                            │
╰─────────────────────────────────────────────────────────╯
```

---

## 6. API Design — All Endpoints

### Base URL: `http://localhost:8000`

### Ingestion Endpoints

| Method | Path | Description | Response |
|---|---|---|---|
| `POST` | `/ingest/image` | Upload receipt/shelf image | 202 + task_id |
| `POST` | `/ingest/voice` | Upload audio file (WAV/MP3) | 202 + task_id |
| `POST` | `/ingest/text` | Natural language text | 202 + task_id |
| `POST` | `/ingest/csv` | Bulk CSV import | 200 + summary |
| `GET` | `/ingest/status/{task_id}` | Check processing status | 200 + result |

### Inventory CRUD Endpoints

| Method | Path | Description | Response |
|---|---|---|---|
| `GET` | `/inventory` | List all items (query params: category, status, sort, search) | 200 + items[] |
| `GET` | `/inventory/{id}` | Get single item | 200 + item |
| `PUT` | `/inventory/{id}` | Update item (quantity, status, etc.) | 200 + updated item |
| `DELETE` | `/inventory/{id}` | Remove item | 204 |
| `GET` | `/inventory/search?q=` | Full-text search | 200 + items[] |

### Review Queue Endpoints

| Method | Path | Description | Response |
|---|---|---|---|
| `GET` | `/review` | List pending review items | 200 + items[] |
| `POST` | `/review/{id}/approve` | Approve and move to active inventory | 200 + item |
| `POST` | `/review/{id}/reject` | Reject and discard | 204 |

### Triage & Forecast Endpoints

| Method | Path | Description | Response |
|---|---|---|---|
| `GET` | `/triage` | Get FEFO-ordered expiring items + AI recipes | 200 + triage_result |
| `POST` | `/triage/generate-recipes` | Force recipe generation for expiring items | 200 + recipes[] |
| `GET` | `/forecast` | Forecast all items with burn-rates | 200 + forecasts[] |
| `GET` | `/forecast/{item_id}` | Forecast specific item | 200 + forecast |

### System Endpoints

| Method | Path | Description | Response |
|---|---|---|---|
| `GET` | `/health` | System health (DB, AI API, disk) | 200 + health_status |
| `GET` | `/audit-log` | View audit trail | 200 + logs[] |
| `GET` | `/metrics` | Carbon impact summary | 200 + metrics |
| `POST` | `/dev/advance-time` | Dev mode: advance simulated time | 200 + new_date |
| `POST` | `/dev/seed-data` | Dev mode: seed synthetic data | 200 + summary |
| `POST` | `/dev/reset` | Dev mode: reset database | 200 |

---

## 7. AI Integration — All Three Input Modes

### Unified Architecture

All three input modes feed into the same pipeline:

```
Input (image/voice/text)
    │
    ├── [text only] → PII Scrubber (pre-AI)
    │
    ▼
┌─────────────────┐     ┌─────────────────┐
│  Gemini 2.5     │────►│  Pydantic       │
│  Flash API      │     │  Validation     │
│  (Structured    │     │  (strict schema)│
│   Output)       │     └────────┬────────┘
└─────────────────┘              │
                                 ▼
                        ┌─────────────────┐
                        │  PII Scrubber   │  ← ALL extracted text fields
                        │  (pre-DB)       │     scrubbed before storage
                        └────────┬────────┘
                          ┌──────┴──────┐
                          │             │
                    confidence     confidence
                     >= 85%         < 85%
                          │             │
                          ▼             ▼
                   ┌────────────┐ ┌──────────────┐
                   │  Active    │ │  Pending     │
                   │  Inventory │ │  Human       │
                   │  + Carbon  │ │  Review      │
                   │  Lookup    │ │  Queue       │
                   └────────────┘ └──────────────┘
```

### Pydantic Schema for Structured Output

```python
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

class ItemUnit(str, Enum):
    """Canonical base units ONLY — no packaging units like packs/bottles/cans."""
    KG = "kg"
    GRAMS = "g"
    LITERS = "L"
    ML = "mL"
    UNITS = "units"   # For countable items (eggs, markers, petri dishes)

class ItemCategory(str, Enum):
    # Dairy — split by product type
    MILK_CREAM = "Milk & Cream"
    CHEESE = "Cheese"
    YOGURT = "Yogurt"
    BUTTER_SPREADS = "Butter & Spreads"
    EGGS = "Eggs"
    # Produce — split by type
    FRESH_FRUIT = "Fresh Fruit"
    FRESH_VEGETABLES = "Fresh Vegetables"
    HERBS_GREENS = "Herbs & Leafy Greens"
    ROOT_VEGETABLES = "Root Vegetables"
    # Meat & Protein — split by type
    POULTRY = "Poultry"
    RED_MEAT = "Red Meat"
    SEAFOOD = "Seafood"
    # Bakery — split by type
    BREAD = "Bread & Rolls"
    PASTRY = "Pastry & Cakes"
    # Pantry Staples — split by type
    GRAINS_RICE = "Grains & Rice"
    PASTA = "Pasta & Noodles"
    COOKING_OIL = "Cooking Oils & Vinegar"
    CONDIMENTS = "Condiments & Sauces"
    SUGAR_SWEETENER = "Sugar & Sweeteners"
    NUTS_SEEDS = "Nuts & Seeds"
    CANNED_PRESERVED = "Canned & Preserved"
    # Beverages — split by type
    COFFEE_TEA = "Coffee & Tea"
    JUICE_DRINKS = "Juice & Soft Drinks"
    PLANT_MILK = "Plant-Based Milk"
    # Non-Food
    OFFICE_PAPER = "Office - Paper"
    OFFICE_SUPPLIES = "Office - Supplies"
    CLEANING = "Cleaning Products"
    LAB_CHEMICALS = "Lab Chemicals"
    LAB_EQUIPMENT = "Lab Equipment"
    OTHER = "Other"

class ExtractedItem(BaseModel):
    item_name: str = Field(description="Canonical singular lowercase English name")
    quantity: float = Field(description="Quantity converted to base metric unit", ge=0)
    unit: ItemUnit = Field(description="Canonical base unit (kg, g, L, mL, or units)")
    raw_input_text: str = Field(description="Original text as it appeared in input, for audit")
    category: ItemCategory = Field(description="Category of the item")
    expiry_date: Optional[str] = Field(
        description="Expiry date in YYYY-MM-DD format, null if not perishable or not specified",
        default=None
    )
    confidence_score: float = Field(
        description="Your confidence in this extraction from 0.0 to 1.0",
        ge=0.0, le=1.0
    )

class ExtractionResult(BaseModel):
    items: list[ExtractedItem] = Field(description="List of extracted inventory items")
    source_description: str = Field(description="Brief description of the source input")
```

### Mode 1: Image Input (📷)

**CLI:** `eco-pulse ingest --image receipt.jpg`

**Pipeline:**
1. Read image file from disk
2. Send to Gemini 2.5 Flash with structured output prompt
3. Gemini returns `ExtractionResult` as JSON
4. Validate via Pydantic
5. Route based on confidence score

**Gemini API Call:**
```python
from google import genai
from google.genai import types

client = genai.Client(api_key=settings.gemini_api_key)

# Upload image
with open(image_path, "rb") as f:
    image_bytes = f.read()

mime_type = "image/jpeg"  # or detect from extension

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=[
        types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
        types.Part.from_text(EXTRACTION_PROMPT),
    ],
    config={
        "response_mime_type": "application/json",
        "response_json_schema": ExtractionResult.model_json_schema(),
    },
)

result = ExtractionResult.model_validate_json(response.text)
```

**Supported Image Formats:** JPEG, PNG, WebP, GIF, BMP

### Mode 2: Voice Input (🎙️)

**CLI:** `eco-pulse ingest --voice` (live recording) or `eco-pulse ingest --voice --file sample.wav` (pre-recorded)

**Pipeline:**
1. **If `--file` is provided:** Use the specified audio file directly
2. **If no `--file`:** Check for audio hardware availability. If unavailable (e.g., Docker container), prompt user for a file path instead of crashing
3. CLI prompts "Press Enter to start recording, Enter again to stop" (live mode only)
4. Record audio via `sounddevice` library to WAV file (live mode only)
5. Send WAV to Gemini 2.5 Flash with structured output prompt
6. Same pipeline as image (validate → route)

**Audio Recording (CLI):**
```python
import sounddevice as sd
import soundfile as sf

def record_audio(output_path: str, sample_rate: int = 16000):
    """Record until user presses Enter again."""
    print("🎙️  Recording... Press Enter to stop.")
    frames = []
    recording = True

    def callback(indata, frame_count, time_info, status):
        if recording:
            frames.append(indata.copy())

    stream = sd.InputStream(samplerate=sample_rate, channels=1, callback=callback)
    stream.start()
    input()  # Wait for Enter
    recording = False
    stream.stop()

    audio = np.concatenate(frames)
    sf.write(output_path, audio, sample_rate)
```

**Gemini API Call (Audio):**
```python
with open(audio_path, "rb") as f:
    audio_bytes = f.read()

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=[
        types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav"),
        types.Part.from_text(EXTRACTION_PROMPT),
    ],
    config={
        "response_mime_type": "application/json",
        "response_json_schema": ExtractionResult.model_json_schema(),
    },
)
```

**Supported Audio Formats:** WAV, MP3, AIFF, AAC, OGG, FLAC

### Mode 3: Text Input (✏️)

**CLI:** `eco-pulse ingest --text "Bought 50 organic apples, expires next Tuesday"`

**Pipeline:**
1. Apply PII scrubber to text - have a dummy regex - not in scope for current prototype
2. Send text to Gemini with structured output prompt
3. Same validation + routing pipeline

**Gemini API Call (Text):**
```python
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=f"{EXTRACTION_PROMPT}\n\nUser input: {scrubbed_text}",
    config={
        "response_mime_type": "application/json",
        "response_json_schema": ExtractionResult.model_json_schema(),
    },
)
```

### The Extraction Prompt (Shared Across All Modes)

```python
EXTRACTION_PROMPT = """
You are an inventory data extraction assistant for a small business/cafe/non-profit.

Extract ALL inventory items from the provided input (image, audio, or text).

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
```

### Recipe Generation Prompt

```python
RECIPE_PROMPT = """
You are a creative chef assistant helping a small cafe reduce food waste.

The following items are expiring soon and need to be used up:
{expiring_items_json}

Generate up to 5 practical recipes that:
1. Use AS MANY of the expiring items as possible
2. Are simple enough for a small cafe kitchen
3. Could be sold as a "Special of the Day"
4. Minimize additional ingredient purchases

For each recipe, specify which expiring items it uses and approximate servings.
Prioritize recipes that use the MOST URGENTLY expiring items first.
"""
```

### Recipe Pydantic Schema

```python
class Recipe(BaseModel):
    title: str = Field(description="Name of the recipe")
    ingredients_used: list[str] = Field(description="List of expiring item names used")
    additional_ingredients: list[str] = Field(description="Any extra ingredients needed")
    instructions: str = Field(description="Step-by-step cooking instructions")
    estimated_servings: int = Field(description="Number of servings")
    difficulty: str = Field(description="Easy, Medium, or Hard")

class RecipeResponse(BaseModel):
    recipes: list[Recipe] = Field(description="List of generated recipes")
    items_not_used: list[str] = Field(description="Expiring items not included in any recipe")
```

---

## 7b. Input Standardization & Deduplication Pipeline

This pipeline ensures data quality by normalizing every field before it reaches the database. It operates in **3 layers** — AI-level guidance, deterministic Python normalization, and database-level deduplication.

### The Problem

| Input Variant | Without Standardization | With Standardization |
|---|---|---|
| "5 apples" vs "5 apple" | 2 separate DB rows | Same item: `apple`, merged quantity |
| "aluminium foil" vs "aluminum foil" | 2 rows | Same item: `aluminum foil` |
| "1 pack of rice" vs "1 kg rice" | Incomparable quantities | Both stored as `g` or `kg` |
| "1 cup of milk" vs "250 mL milk" | Different units | Both stored as `mL` (1 cup = 240 mL) |
| "Whole Milk" vs "whole milk" | 2 rows | Same item: `whole milk` |
| "2 dozen eggs" vs "24 eggs" | Different quantities | Both: `24 units` |

### Layer 1: AI-Level Normalization (in the Extraction Prompt)

The extraction prompt (Section 7) already instructs Gemini to:
- Return **singular, lowercase** item names ("apple" not "Apples")
- Use **US English spelling** ("aluminum" not "aluminium")
- Convert quantities to **base metric units** (cups→mL, packs→g, dozen→units)
- Use only **5 canonical units**: `kg`, `g`, `L`, `mL`, `units`
- Preserve the **raw input text** separately for audit trail

This handles ~80% of normalization. But AI can be inconsistent, so we need deterministic backup.

### Layer 2: Deterministic Python Normalization (Post-Extraction)

After Gemini returns structured data, apply these rules in code:

```python
import re
from typing import Optional

# ---- Name Normalization ----

# Common spelling variants → canonical US English
SPELLING_MAP = {
    "aluminium": "aluminum",
    "colour": "color",
    "flavour": "flavor",
    "yoghurt": "yogurt",
    "grey": "gray",
    "litre": "liter",
    "metre": "meter",
    "catalogue": "catalog",
    "cheque": "check",
    "tonne": "metric ton",
}

# Simple plural → singular rules (covers 90% of English nouns)
def singularize(word: str) -> str:
    """Rule-based singularization. Handles common English plural patterns."""
    if len(word) <= 2:
        return word
    # Irregular plurals
    irregulars = {
        "tomatoes": "tomato", "potatoes": "potato", "mangoes": "mango",
        "loaves": "loaf", "knives": "knife", "shelves": "shelf",
        "mice": "mouse", "geese": "goose", "teeth": "tooth",
        "oxen": "ox", "children": "child", "fish": "fish",
    }
    if word in irregulars:
        return irregulars[word]
    # Rules in order of specificity
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"       # berries → berry
    if word.endswith("ves"):
        return word[:-3] + "f"       # loaves → loaf (if not in irregulars)
    if word.endswith("ses") or word.endswith("xes") or word.endswith("zes"):
        return word[:-2]             # boxes → box, gases → gas
    if word.endswith("shes") or word.endswith("ches"):
        return word[:-2]             # dishes → dish, watches → watch
    if word.endswith("s") and not word.endswith("ss"):
        return word[:-1]             # apples → apple (but not "glass")
    return word


def normalize_item_name(name: str) -> str:
    """
    Deterministic name normalization:
    1. Lowercase + strip whitespace
    2. Apply spelling map
    3. Singularize each word
    4. Sort multi-word names consistently ("milk whole" → "whole milk" via canonical form)
    """
    # Step 1: Lowercase + strip + collapse whitespace
    name = re.sub(r'\s+', ' ', name.strip().lower())

    # Step 2: Apply spelling corrections word-by-word
    words = name.split()
    words = [SPELLING_MAP.get(w, w) for w in words]

    # Step 3: Singularize each word
    words = [singularize(w) for w in words]

    return " ".join(words)


# ---- Unit Normalization ----

# Conversion table → always normalize to the SMALLER canonical unit
# (g for solids, mL for liquids) to avoid floating point issues with small quantities
UNIT_CONVERSIONS = {
    # Volume
    "cup":         {"mL": 240},
    "cups":        {"mL": 240},
    "tbsp":        {"mL": 15},
    "tablespoon":  {"mL": 15},
    "tsp":         {"mL": 5},
    "teaspoon":    {"mL": 5},
    "gallon":      {"L": 3.785},
    "gal":         {"L": 3.785},
    "pint":        {"mL": 473},
    "quart":       {"mL": 946},
    "fl oz":       {"mL": 29.57},
    # Weight
    "lb":          {"g": 453.6},
    "lbs":         {"g": 453.6},
    "pound":       {"g": 453.6},
    "oz":          {"g": 28.35},
    "ounce":       {"g": 28.35},
    # Counting
    "dozen":       {"units": 12},
    "pair":        {"units": 2},
    "gross":       {"units": 144},
    "ream":        {"units": 500},  # Paper
}

# Common pack sizes when AI couldn't resolve (fallback estimates)
DEFAULT_PACK_SIZES = {
    "rice":          {"g": 1000},    # 1 pack of rice ≈ 1kg
    "pasta":         {"g": 500},     # 1 pack of pasta ≈ 500g
    "butter":        {"g": 250},     # 1 pack of butter ≈ 250g
    "sugar":         {"g": 1000},    # 1 pack of sugar ≈ 1kg
    "flour":         {"g": 1000},    # 1 pack of flour ≈ 1kg
    "coffee bean":   {"g": 500},     # 1 pack of coffee ≈ 500g
    "napkin":        {"units": 100}, # 1 pack of napkins ≈ 100
    "paper towel":   {"units": 6},   # 1 pack = 6 rolls
}


def normalize_quantity_and_unit(quantity: float, unit: str, item_name: str) -> tuple[float, str]:
    """
    Normalize quantity + unit to canonical base units.
    Returns (normalized_quantity, canonical_unit).
    """
    unit_lower = unit.strip().lower()

    # Already canonical?
    if unit_lower in ("kg", "g", "l", "ml", "units"):
        # Normalize casing
        canonical_map = {"kg": "kg", "g": "g", "l": "L", "ml": "mL", "units": "units"}
        return (quantity, canonical_map[unit_lower])

    # Known unit conversion?
    if unit_lower in UNIT_CONVERSIONS:
        conv = UNIT_CONVERSIONS[unit_lower]
        target_unit = list(conv.keys())[0]
        factor = conv[target_unit]
        return (round(quantity * factor, 2), target_unit)

    # "pack" / "packs" / "package" → look up default pack sizes
    if unit_lower in ("pack", "packs", "package", "packages", "bag", "bags"):
        normalized_name = normalize_item_name(item_name)
        if normalized_name in DEFAULT_PACK_SIZES:
            conv = DEFAULT_PACK_SIZES[normalized_name]
            target_unit = list(conv.keys())[0]
            factor = conv[target_unit]
            return (round(quantity * factor, 2), target_unit)
        else:
            # Unknown pack size — keep as units, flag for review
            return (quantity, "units")

    # "bottle" / "can" → treat as units (the AI should have resolved the volume)
    if unit_lower in ("bottle", "bottles", "can", "cans", "box", "boxes",
                      "carton", "cartons", "jar", "jars"):
        return (quantity, "units")

    # Unknown unit — keep as-is but log warning
    return (quantity, unit)


# ---- Auto-Upscale Small Units ----

def auto_upscale_unit(quantity: float, unit: str) -> tuple[float, str]:
    """
    Upscale small units for readability:
    - 1500g → 1.5kg
    - 2000mL → 2L
    Keeps everything consistent in the DB.
    """
    if unit == "g" and quantity >= 1000:
        return (round(quantity / 1000, 3), "kg")
    if unit == "mL" and quantity >= 1000:
        return (round(quantity / 1000, 3), "L")
    return (quantity, unit)


def convert_to_target_unit(quantity: float, from_unit: str, to_unit: str) -> tuple[float, str]:
    """
    Convert a quantity between compatible unit families for merging during dedup.
    Supports: g <-> kg, mL <-> L. Incompatible families raise ValueError.

    Implementation plan:
    - Define conversion factors: {('g','kg'): 0.001, ('kg','g'): 1000, ('mL','L'): 0.001, ('L','mL'): 1000}
    - If from_unit == to_unit, return as-is
    - If (from_unit, to_unit) in conversion table, multiply and return
    - If units are incompatible (e.g., 'g' -> 'L'), raise ValueError
    - Round result to 3 decimal places to avoid floating point artifacts
    """
    CONVERSIONS = {
        ("g", "kg"): 0.001,
        ("kg", "g"): 1000,
        ("mL", "L"): 0.001,
        ("L", "mL"): 1000,
    }
    if from_unit == to_unit:
        return (quantity, to_unit)
    key = (from_unit, to_unit)
    if key not in CONVERSIONS:
        raise ValueError(f"Cannot convert {from_unit} to {to_unit}: incompatible unit families")
    return (round(quantity * CONVERSIONS[key], 3), to_unit)
```

### Layer 3: Database-Level Deduplication (Before Insert)

Before inserting a new item, check if it already exists in inventory. If yes, **merge** by adding quantities.

```python
from difflib import SequenceMatcher

async def find_existing_item(item_name: str, category: str) -> Optional[dict]:
    """
    Find an existing inventory item that matches the incoming item.
    Uses exact match first, then fuzzy matching as fallback.
    """
    normalized_name = normalize_item_name(item_name)

    # Step 1: Exact match on normalized name + category
    exact = await db.query(
        "SELECT * FROM inventory_items WHERE "
        "LOWER(item_name) = ? AND category = ? AND status = 'ACTIVE'",
        [normalized_name, category]
    )
    if exact:
        return exact[0]

    # Step 2: Fuzzy match — catches "whole milk" vs "milk, whole" etc.
    all_items = await db.query(
        "SELECT * FROM inventory_items WHERE category = ? AND status = 'ACTIVE'",
        [category]
    )
    for existing in all_items:
        similarity = SequenceMatcher(
            None, normalized_name, existing["item_name"].lower()
        ).ratio()
        if similarity >= 0.85:  # 85% similar = same item
            return existing

    return None  # Genuinely new item


async def upsert_inventory_item(extracted: ExtractedItem, carbon_score: float, input_method: str):
    """
    Insert or merge an item into inventory:
    - If item exists → ADD to existing quantity (and update expiry if sooner)
    - If new item → INSERT new row
    """
    # Normalize all fields
    normalized_name = normalize_item_name(extracted.item_name)
    qty, unit = normalize_quantity_and_unit(
        extracted.quantity, extracted.unit, extracted.item_name
    )
    qty, unit = auto_upscale_unit(qty, unit)

    # Check for existing item
    existing = await find_existing_item(normalized_name, extracted.category)

    if existing:
        # MERGE: Convert units if needed, then add quantities
        if existing["unit"] == unit:
            new_qty = existing["quantity"] + qty
        else:
            # Unit mismatch — convert incoming to match existing
            new_qty, _ = convert_to_target_unit(qty, unit, existing["unit"])
            new_qty = existing["quantity"] + new_qty
            unit = existing["unit"]

        # Update expiry to the SOONER date (more conservative)
        new_expiry = existing["expiry_date"]
        if extracted.expiry_date:
            if not new_expiry or extracted.expiry_date < new_expiry:
                new_expiry = extracted.expiry_date

        await db.update_item(
            item_id=existing["id"],
            quantity=new_qty,
            expiry_date=new_expiry,
        )
        await log_audit("ITEM_MERGED", details={
            "existing_item": existing["item_name"],
            "incoming_name": extracted.item_name,
            "added_qty": qty,
            "new_total": new_qty,
            "unit": unit,
        })
        return {"action": "MERGED", "item_id": existing["id"], "new_qty": new_qty}
    else:
        # INSERT: New item
        item_id = await db.insert_inventory_item_normalized(
            item_name=normalized_name,
            quantity=qty,
            unit=unit,
            category=extracted.category,
            expiry_date=extracted.expiry_date,
            co2_per_unit_kg=carbon_score,
            confidence_score=extracted.confidence_score,
            input_method=input_method,
        )
        return {"action": "INSERTED", "item_id": item_id}
```

### The Complete Normalization Flow

```
Raw Input ("Bought 2 packs of Organic Apples and 1 gallon Whole Milk")
    │
    ▼
┌──────────────────────────────────────────────────────────────────┐
│  LAYER 1: AI Extraction (Gemini 2.5 Flash)                      │
│  Prompt instructs: singular, lowercase, base metric units        │
│                                                                  │
│  → {item_name: "organic apple", qty: 2, unit: "packs",          │
│     raw_input_text: "2 packs of Organic Apples"}                 │
│  → {item_name: "whole milk", qty: 3.785, unit: "L",             │
│     raw_input_text: "1 gallon Whole Milk"}                       │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│  LAYER 2: Python Normalization (deterministic)                   │
│                                                                  │
│  normalize_item_name("organic apple")                            │
│    → lowercase ✓, singular ✓, spelling ✓ → "organic apple"      │
│                                                                  │
│  normalize_quantity_and_unit(2, "packs", "organic apple")        │
│    → not in DEFAULT_PACK_SIZES → (2, "units")                   │
│                                                                  │
│  normalize_quantity_and_unit(3.785, "L", "whole milk")           │
│    → already canonical → (3.785, "L")                            │
│                                                                  │
│  auto_upscale_unit → no change needed                            │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│  LAYER 3: Database Dedup (fuzzy match)                           │
│                                                                  │
│  find_existing_item("organic apple", "Produce")                  │
│    → Found! Existing: {name: "organic apple", qty: 30, unit: u}  │
│    → MERGE: 30 + 2 = 32 units                                   │
│                                                                  │
│  find_existing_item("whole milk", "Dairy")                       │
│    → Found! Existing: {name: "whole milk", qty: 5, unit: L}      │
│    → MERGE: 5 + 3.785 = 8.785 L                                 │
└──────────────────────────────────────────────────────────────────┘
```

### Edge Case Handling

| Edge Case | How It's Handled |
|---|---|
| "1 pack of rice" (ambiguous weight) | AI tries to estimate → if it says "packs", Layer 2 checks `DEFAULT_PACK_SIZES` → rice = 1000g per pack → stored as 1000g |
| "1 cup of rice" vs "150g of rice" | AI converts cup→185g. Layer 2 verifies unit is canonical. Both stored in `g`. Dedup merges: 185 + 150 = 335g |
| "Apples" vs "apple" vs "APPLE" | AI returns "apple" (prompted for singular lowercase). Layer 2 confirms via `singularize()` + `lower()`. Dedup exact-matches |
| "aluminium foil" vs "aluminum foil" | AI prompted for US English. Layer 2 applies `SPELLING_MAP`. Both become "aluminum foil" |
| "Milk" vs "Whole Milk" vs "Skim Milk" | AI prompted to be specific. These are genuinely different items → stored separately (correct behavior) |
| "2 bottles of OJ" | AI extracts volume (e.g., 2L). If AI says "bottles", Layer 2 converts to "units" — but ideally AI resolves to mL/L |
| Unit mismatch on merge (existing=kg, incoming=g) | `convert_to_target_unit()` converts g→kg before adding |
| Completely unknown item + unknown pack size | Stored as `units`. AI confidence lowered. Audit log flags it |

### Why 3 Layers?

> **Layer 1 (AI)** handles the hard, contextual cases — it knows that "1 cup of rice" is ~185g and "1 pack of butter" is 250g. But AI can be inconsistent.
>
> **Layer 2 (Python)** is deterministic and fast — it guarantees lowercase, singular, correct spelling, canonical units. It catches everything the AI missed.
>
> **Layer 3 (DB Dedup)** is the safety net — even if two items have slightly different names ("whole milk" vs "milk whole"), fuzzy matching catches it and merges instead of duplicating.

---

## 8. Fallback Engineering — Complete Matrix

This is the **key differentiator** for the AI Application scoring metric. We have **5 distinct fallback paths**:

### Fallback Matrix

| # | Trigger Condition | Detection Method | Fallback Action | DB Routing | Audit Log Entry |
|---|---|---|---|---|---|
| **F1** | LLM confidence < 85% | Check `confidence_score` field in response | Route to `pending_human_review` table | `pending_human_review` | `AI_FALLBACK: LOW_CONFIDENCE` |
| **F2** | LLM response fails Pydantic validation | `ValidationError` exception from Pydantic | **Retry once** with the validation error appended to the prompt so the model can self-correct. If retry also fails → route to `pending_human_review` with raw response | `pending_human_review` (after retry fails) | `AI_FALLBACK: VALIDATION_FAILED` (includes retry count) |
| **F3** | LLM API timeout (> 60 seconds) | `asyncio.timeout(60.0)` or `httpx.TimeoutException` | Route to `pending_human_review` for human resolution. **No auto-discount** — human decides the action | `pending_human_review` | `AI_FALLBACK: TIMEOUT` |
| **F4** | LLM API rate limit (429) | `google.api_core.exceptions.ResourceExhausted` or HTTP 429 | Parse `Retry-After` header. **Wait and retry** after the specified delay. **Notify user** about the rate limit and ETA. If retry also fails → route to `pending_human_review` | `pending_human_review` (after retry fails) | `AI_FALLBACK: RATE_LIMITED` (includes wait time + retry result) |
| **F4b** | LLM API error (auth, network, other) | `google.api_core.exceptions.*` or `ConnectionError` | Route to `pending_human_review` for human resolution. **Notify user** about the specific error | `pending_human_review` | `AI_FALLBACK: API_ERROR` |
| **F5** | LLM returns empty/null response | Check for None/empty `items` list | **Retry once** with a rephrased prompt asking for more careful extraction. If retry also returns empty → prompt user for manual entry via CLI | Interactive CLI prompt (after retry fails) | `AI_FALLBACK: EMPTY_RESPONSE` (includes retry count) |

### Fallback F1: Low Confidence Routing (Detailed)

```python
async def process_extraction_result(result: ExtractionResult, input_method: str):
    for item in result.items:
        if item.confidence_score < settings.confidence_threshold:  # 0.85
            # Route to pending review
            await db.insert_pending_review(
                raw_input=str(item),
                llm_response=item.model_dump_json(),
                confidence_score=item.confidence_score,
                failure_reason="LOW_CONFIDENCE",
                suggested_item_name=item.item_name,
                suggested_quantity=item.quantity,
            )
            await log_audit("AI_FALLBACK", severity="WARN",
                          details={"reason": "LOW_CONFIDENCE", "score": item.confidence_score})
        else:
            # Route to active inventory
            # Carbon lookup: check Green DB first, if unknown → ask AI → update table
            carbon_score = await lookup_carbon_impact(item.item_name, item.category)
            await db.insert_inventory_item(item, carbon_score, input_method)
            await log_audit("INGESTION", details={"item": item.item_name, "method": input_method})
```

### Carbon Impact Lookup — AI Fallback for Unknown Items

```python
async def lookup_carbon_impact(item_name: str, category: str) -> float:
    """
    Look up the CO₂ impact for an item:
    1. Check the carbon_impact_db table (fuzzy match on item_name)
    2. If not found → ask Gemini to estimate the CO₂/unit
    3. Persist the AI estimate back into carbon_impact_db for future lookups
    """
    # Step 1: Try local lookup (exact or fuzzy match)
    match = await db.fuzzy_match_carbon_db(item_name)
    if match:
        return match["co2_per_unit_kg"]

    # Step 2: Item not in Green DB → ask AI for an estimate
    try:
        response = await client.models.generate_content(
            model=settings.model_name,
            contents=(
                f"Estimate the carbon footprint (kg CO₂ per unit) for this item: "
                f"{item_name} (category: {category}). "
                f"Base your estimate on lifecycle analysis data. "
                f"Return ONLY a JSON object with: "
                f'{{"co2_per_unit_kg": <float>, "avg_shelf_life_days": <int or null>, "source": "AI estimate"}}'
            ),
            config={
                "response_mime_type": "application/json",
                "response_json_schema": CarbonEstimate.model_json_schema(),
            },
        )
        estimate = CarbonEstimate.model_validate_json(response.text)

        # Step 3: Persist to carbon_impact_db so future lookups are instant
        await db.insert_carbon_item(
            item_name=item_name,
            category=category,
            co2_per_unit_kg=estimate.co2_per_unit_kg,
            avg_shelf_life_days=estimate.avg_shelf_life_days,
            preferred_partner="N/A",
        )
        await log_audit("CARBON_AI_ESTIMATE", severity="INFO",
                      details={"item": item_name, "co2": estimate.co2_per_unit_kg,
                               "note": "AI-estimated, persisted to Green DB"})
        return estimate.co2_per_unit_kg

    except Exception as e:
        # AI also failed — use 0.0 as last resort (will be updated later)
        await log_audit("CARBON_LOOKUP_FAILED", severity="WARN",
                      details={"item": item_name, "error": str(e)})
        return 0.0


class CarbonEstimate(BaseModel):
    co2_per_unit_kg: float = Field(description="Estimated kg CO₂ per unit")
    avg_shelf_life_days: Optional[int] = Field(description="Estimated shelf life in days", default=None)
    source: str = Field(default="AI estimate")
```

### Fallback F2: Validation Failure — Retry Once With Error (Detailed)

```python
async def call_gemini_with_validation_retry(contents: list, schema, max_retries: int = 1):
    """
    Call Gemini and validate response. If Pydantic validation fails,
    retry ONCE with the error message appended to the prompt so the
    model can self-correct. If retry also fails → route to pending review.
    """
    last_error = None
    response = None

    for attempt in range(max_retries + 1):
        try:
            if attempt > 0 and last_error:
                # Append the validation error to help the model self-correct
                error_hint = types.Part.from_text(
                    f"\n\nYour previous response failed validation with this error: "
                    f"{last_error}\n\nPlease fix the output to match the schema exactly."
                )
                contents = contents + [error_hint]
                await log_audit("AI_RETRY", severity="INFO",
                              details={"attempt": attempt + 1, "error": str(last_error)})

            response = await client.models.generate_content(
                model=settings.model_name,
                contents=contents,
                config={
                    "response_mime_type": "application/json",
                    "response_json_schema": schema,
                },
            )
            result = ExtractionResult.model_validate_json(response.text)
            return result  # Success!

        except (ValidationError, ValueError) as e:
            last_error = e
            if attempt >= max_retries:
                # All retries exhausted — route to human review
                await db.insert_pending_review(
                    raw_input=str(contents),
                    llm_response=response.text if response else None,
                    confidence_score=None,
                    failure_reason="VALIDATION_FAILED",
                )
                await log_audit("AI_FALLBACK", severity="WARN",
                              details={"reason": "VALIDATION_FAILED",
                                       "attempts": attempt + 1,
                                       "error": str(last_error)})
                raise  # Re-raise for caller to handle
```

### Fallback F3: Timeout → Human Review (Detailed)

```python
async def triage_expiring_item(item_id: str):
    """
    Attempt AI-powered triage with a generous 60-second timeout.
    On timeout: NO auto-discount. Route to human review instead —
    humans decide the appropriate action for the expiring item.
    """
    item = await db.get_item(item_id)

    try:
        async with asyncio.timeout(60.0):  # 60 seconds — generous for AI
            recipes = await generate_recipes_with_ai([item])
            await db.insert_triage_action(
                item_id=item_id,
                action_type="RECIPE_GENERATED",
                ai_generated=True,
                ai_bypassed=False,
                content=recipes.model_dump_json()
            )
    except (TimeoutError, asyncio.TimeoutError):
        # FALLBACK F3: Route to human review — NO auto-discount
        await db.insert_pending_review(
            raw_input=f"Triage timeout for: {item['item_name']} (qty: {item['quantity']})",
            llm_response=None,
            confidence_score=None,
            failure_reason="TIMEOUT",
            suggested_item_name=item["item_name"],
            suggested_quantity=item["quantity"],
        )
        await log_audit("AI_FALLBACK", severity="WARN",
                      details={"reason": "TIMEOUT", "item_id": item_id,
                               "action": "ROUTED_TO_HUMAN_REVIEW",
                               "note": "Human must decide: discount, donate, or recipe"})
        return TriageResult(
            action_taken="PENDING_HUMAN_REVIEW",
            ai_generated=False,
            ai_bypassed=True,
            message="AI timed out after 60s. Item routed to human review queue."
        )
```

### Fallback F4: Rate Limit — Wait, Retry, Notify User (Detailed)

```python
import google.api_core.exceptions

async def call_gemini_with_rate_limit_handling(contents: list, schema, notify_callback=None):
    """
    Handle Gemini API rate limits (HTTP 429) gracefully:
    1. Parse Retry-After header for wait time
    2. Notify user about the rate limit and ETA
    3. Retry with exponential backoff (up to 3 attempts)
    4. If all retries fail → route to pending review + notify user
    """
    max_retries = 3

    try:
        response = await client.models.generate_content(
            model=settings.model_name,
            contents=contents,
            config={
                "response_mime_type": "application/json",
                "response_json_schema": schema,
            },
        )
        return ExtractionResult.model_validate_json(response.text)

    except google.api_core.exceptions.ResourceExhausted as e:
        # Rate limited (HTTP 429) — extract base retry delay
        base_retry_after = getattr(e, 'retry_after', None) or 30  # Default 30s

        for attempt in range(max_retries):
            # Exponential backoff: base * 2^attempt, capped at 120s
            delay = min(base_retry_after * (2 ** attempt), 120)

            if notify_callback:
                notify_callback(
                    f"⚠️  AI rate limit reached. Retrying in {delay}s "
                    f"(attempt {attempt + 1}/{max_retries})..."
                )
            await log_audit("AI_RATE_LIMITED", severity="WARN",
                          details={"retry_after_seconds": delay, "attempt": attempt + 1})

            await asyncio.sleep(delay)

            try:
                response = await client.models.generate_content(
                    model=settings.model_name,
                    contents=contents,
                    config={
                        "response_mime_type": "application/json",
                        "response_json_schema": schema,
                    },
                )
                if notify_callback:
                    notify_callback(f"✅ Retry successful after {attempt + 1} attempt(s).")
                return ExtractionResult.model_validate_json(response.text)

            except google.api_core.exceptions.ResourceExhausted:
                if attempt == max_retries - 1:
                    # All retries exhausted
                    if notify_callback:
                        notify_callback(
                            f"❌ All {max_retries} retries failed. "
                            f"Item routed to human review queue."
                        )
                    await log_audit("AI_FALLBACK", severity="ERROR",
                                  details={"reason": "RATE_LIMITED_RETRIES_EXHAUSTED",
                                           "total_attempts": max_retries,
                                           "total_wait": sum(min(base_retry_after * (2**i), 120) for i in range(max_retries))})
                    raise  # Caller handles routing to pending_human_review
                continue  # Try next backoff level

            except Exception as retry_error:
                # Non-rate-limit error during retry
                if notify_callback:
                    notify_callback(
                        f"❌ Retry failed: {type(retry_error).__name__}. "
                        f"Item routed to human review queue."
                    )
                await log_audit("AI_FALLBACK", severity="ERROR",
                              details={"reason": "RATE_LIMITED_RETRY_FAILED",
                                       "attempt": attempt + 1,
                                       "retry_error": str(retry_error)})
                raise  # Caller handles routing to pending_human_review

    except ConnectionError as e:
        # F4b: Network/auth error — notify user and route to human review
        if notify_callback:
            notify_callback(
                f"❌ API connection failed: {type(e).__name__}. "
                f"Item routed to human review queue."
            )
        await log_audit("AI_FALLBACK", severity="ERROR",
                      details={"reason": "API_ERROR", "error": str(e)})
        raise  # Caller handles routing to pending_human_review
```

### Fallback F5: Empty Response — Retry Once Then Manual (Detailed)

```python
async def handle_empty_response(original_contents: list, schema, input_method: str):
    """
    LLM returned zero items. Retry ONCE with a rephrased prompt
    that asks the model to look more carefully. If retry also returns
    empty → fall back to manual CLI entry.
    """
    # Retry with a more explicit prompt
    retry_prompt = types.Part.from_text(
        "\n\nYour previous extraction returned zero items. "
        "Please look more carefully at the input. Even if the quality is poor, "
        "extract ANY items you can identify, even with low confidence scores. "
        "If you truly cannot find any items, return an empty items list."
    )
    retry_contents = original_contents + [retry_prompt]

    await log_audit("AI_RETRY", severity="INFO",
                  details={"reason": "EMPTY_RESPONSE", "attempt": 2})

    try:
        response = await client.models.generate_content(
            model=settings.model_name,
            contents=retry_contents,
            config={
                "response_mime_type": "application/json",
                "response_json_schema": schema,
            },
        )
        result = ExtractionResult.model_validate_json(response.text)

        if result.items:  # Retry found items!
            await log_audit("AI_RETRY_SUCCESS", severity="INFO",
                          details={"items_found": len(result.items)})
            return result
    except Exception:
        pass  # Retry failed — fall through to manual entry

    # Both attempts returned empty — fall back to manual entry
    await log_audit("AI_FALLBACK", severity="WARN",
                  details={"reason": "EMPTY_RESPONSE", "attempts": 2,
                           "action": "MANUAL_ENTRY"})
    return manual_entry_fallback()


def manual_entry_fallback():
    """Interactive CLI manual entry — only after AI retry has also failed."""
    console.print("[yellow]⚠️  AI could not extract items after 2 attempts. "
                  "Falling back to manual entry.[/yellow]")
    item_name = typer.prompt("Item name")
    quantity = typer.prompt("Quantity", type=float)
    unit = typer.prompt("Unit (kg/g/L/mL/units)")
    expiry = typer.prompt("Expiry date (YYYY-MM-DD or empty)", default="")
    category = typer.prompt("Category (e.g., Milk & Cream, Fresh Fruit, Poultry, Bread & Rolls, Other)")

    return ExtractionResult(
        items=[ExtractedItem(
            item_name=item_name, quantity=quantity, unit=unit,
            category=category, expiry_date=expiry or None,
            confidence_score=1.0  # Manual entry = 100% confidence
        )],
        source_description="Manual entry (AI fallback after 2 failed attempts)"
    )
```

### Community Mesh Fallback (Stub/Mock Implementation)

```python
async def community_mesh_check(item_id: str, item_name: str, quantity: float):
    """
    STUB: Checks if any partner organizations need the expiring item.
    In production, this would query a partner API or send actual emails.
    For the hackathon, we mock the check and log the action.
    """
    # Mock partner database
    partners = await db.get_partner_for_item(item_name)

    if partners:
        # Draft a mock email payload (not actually sent)
        email_payload = {
            "to": partners[0]["email"],
            "subject": f"Available: {quantity} units of {item_name}",
            "body": f"We have {quantity} units of {item_name} expiring soon. "
                    f"Would your organization like to receive this donation?",
        }
        await db.insert_triage_action(
            item_id=item_id,
            action_type="COMMUNITY_MESH",
            ai_generated=False,
            ai_bypassed=False,
            content=json.dumps(email_payload),
        )
        await log_audit("COMMUNITY_MESH", details={
            "partner": partners[0]["name"],
            "item": item_name,
            "note": "MOCK — email not actually sent"
        })
        return {"status": "DONATION_DRAFTED", "partner": partners[0]["name"]}
    else:
        return {"status": "NO_PARTNER_FOUND"}
```

---

## 9. Predictive Analytics — Upgraded Regression

### Model: scikit-learn `LinearRegression` with Day-of-Week Features

### Why Not AI for Forecasting?
> **Tradeoff:** LLMs are notoriously unreliable at arithmetic and time-series prediction. Using deterministic linear regression is orders of magnitude faster, computationally cheaper, and 100% reproducible. We reserve AI exclusively for generative tasks (recipes, extraction) where it genuinely excels.

### Feature Engineering

| Feature | Type | Description |
|---|---|---|
| `day_of_week` | One-hot (7 cols) | Monday=0 through Sunday=6, one-hot encoded |
| `is_weekend` | Binary (0/1) | Saturday or Sunday |
| `days_since_start` | Integer | Trend feature — day number from first observation |
| `rolling_avg_7d` | Float | 7-day rolling average of daily consumption |

### Implementation

```python
import numpy as np
from sklearn.linear_model import LinearRegression
from datetime import datetime, timedelta

async def forecast_burn_rate(item_id: str) -> dict:
    """
    Predict when an item will run out using Linear Regression
    with day-of-week seasonality features.
    """
    # Get last 14-30 days of usage events
    events = await db.get_usage_events(item_id, days=30)

    if len(events) < 7:
        return {
            "status": "INSUFFICIENT_DATA",
            "message": f"Need at least 7 days of data, have {len(events)}",
            "days_of_supply": None
        }

    # Aggregate daily consumption
    daily_usage = aggregate_daily_usage(events)

    # Build feature matrix
    X = []
    y = []
    for day_data in daily_usage:
        features = [
            day_data["days_since_start"],           # Trend
            int(day_data["is_weekend"]),             # Weekend flag
            *one_hot_day_of_week(day_data["dow"]),   # 7 day-of-week features
        ]
        X.append(features)
        y.append(day_data["total_consumed"])

    X = np.array(X)
    y = np.array(y)

    # Fit model
    model = LinearRegression()
    model.fit(X, y)
    r_squared = model.score(X, y)

    # Predict future consumption
    current_stock = await db.get_current_quantity(item_id)
    remaining = current_stock
    predict_day = len(daily_usage)
    runout_date = datetime.now()

    while remaining > 0 and predict_day < 365:
        future_date = datetime.now() + timedelta(days=predict_day - len(daily_usage) + 1)
        dow = future_date.weekday()
        is_wkend = 1 if dow >= 5 else 0
        features = [predict_day, is_wkend, *one_hot_day_of_week(dow)]
        predicted_usage = max(0, model.predict([features])[0])
        remaining -= predicted_usage
        runout_date = future_date
        predict_day += 1

    daily_burn_rate = np.mean(y)
    days_of_supply = current_stock / daily_burn_rate if daily_burn_rate > 0 else float('inf')

    return {
        "status": "OK",
        "current_stock": current_stock,
        "daily_burn_rate": round(daily_burn_rate, 2),
        "weekend_multiplier": round(
            (
                np.mean([y[i] for i in range(len(y)) if daily_usage[i]["is_weekend"]])
                / max(np.mean([y[i] for i in range(len(y)) if not daily_usage[i]["is_weekend"]]), 0.01)
            ) if any(d["is_weekend"] for d in daily_usage) else 1.0,
            2
        ),
        "days_of_supply": round(days_of_supply, 1),
        "predicted_runout_date": runout_date.strftime("%Y-%m-%d"),
        "r_squared": round(r_squared, 3),
        "data_points_used": len(y),
    }
```

### Forecast Scheduler

Forecasts are updated automatically via an `asyncio` periodic task launched at FastAPI startup, plus on-demand via CLI:

```python
async def forecast_scheduler(interval_seconds: int = 3600):
    """
    Periodic forecast updater. Runs every `interval_seconds` (default: 1 hour).
    Launched as a background asyncio task on FastAPI startup.

    Implementation plan:
    - Register via @app.on_event("startup") using asyncio.create_task()
    - Loop: await asyncio.sleep(interval_seconds), then call update_all_forecasts()
    - Graceful shutdown: cancel the task in @app.on_event("shutdown")
    - Also callable on-demand via CLI: eco-pulse forecast --refresh
    """
    while True:
        await asyncio.sleep(interval_seconds)
        await update_all_forecasts()
        await log_audit("FORECAST_SCHEDULED", details={"interval": interval_seconds})

async def update_all_forecasts():
    """Recalculate forecasts for all active inventory items."""
    items = await db.get_all_active_items()
    for item in items:
        forecast = await forecast_burn_rate(item["id"])
        await db.upsert_forecast(item["id"], forecast)

        # Auto-trigger triage if running low
        if forecast.get("days_of_supply") and forecast["days_of_supply"] <= 3:
            await triage_expiring_item(item["id"])
```

---

## 10. Grafana Dashboard Specification

### Grafana Setup
- **Image:** `grafana/grafana-oss:latest`
- **Plugin:** `frser-sqlite-datasource` (auto-installed via `GF_INSTALL_PLUGINS` env var)
- **Provisioning:** Auto-loads datasource config + dashboard JSON from mounted volume
- **Default Credentials:** admin/ecopulse (set via env vars)

### Datasource Configuration (`grafana/provisioning/datasources/datasource.yml`)

```yaml
apiVersion: 1
datasources:
  - name: EcoPulse-SQLite
    type: frser-sqlite-datasource
    access: proxy
    isDefault: true
    jsonData:
      path: /data/ecopulse.db
    editable: true
```

### Dashboard Panels (10 Total)

#### Panel 1: 📊 Inventory Overview (Table)
**Type:** Table
**SQL:**
```sql
SELECT
    i.item_name,
    i.category,
    i.quantity,
    i.unit,
    i.expiry_date,
    CAST(julianday(i.expiry_date) - julianday(COALESCE((SELECT value FROM system_config WHERE key = 'simulated_date'), date('now'))) AS INTEGER) as days_left,
    i.status,
    CASE
        WHEN julianday(i.expiry_date) - julianday(COALESCE((SELECT value FROM system_config WHERE key = 'simulated_date'), date('now'))) <= 2 THEN '🔴 URGENT'
        WHEN julianday(i.expiry_date) - julianday(COALESCE((SELECT value FROM system_config WHERE key = 'simulated_date'), date('now'))) <= 7 THEN '🟡 WARNING'
        ELSE '🟢 SAFE'
    END as urgency,
    i.co2_per_unit_kg,
    i.input_method
FROM inventory_items i
WHERE i.status != 'EXPIRED'
ORDER BY
    CASE WHEN i.expiry_date IS NULL THEN 1 ELSE 0 END,
    i.expiry_date ASC
```
**Purpose:** Complete inventory view sorted by FEFO, color-coded urgency levels.

#### Panel 2: 🚨 Expiry Triage Heatmap (Stat + Table)
**Type:** Stat panels + Table
**SQL (Stats):**
```sql
-- Stat 1: Items expiring in 2 days
SELECT COUNT(*) as "Urgent (< 2 days)"
FROM inventory_items
WHERE julianday(expiry_date) - julianday(COALESCE((SELECT value FROM system_config WHERE key = 'simulated_date'), date('now'))) <= 2
  AND status = 'ACTIVE';

-- Stat 2: Items expiring in 7 days
SELECT COUNT(*) as "Warning (< 7 days)"
FROM inventory_items
WHERE julianday(expiry_date) - julianday(COALESCE((SELECT value FROM system_config WHERE key = 'simulated_date'), date('now'))) BETWEEN 3 AND 7
  AND status = 'ACTIVE';

-- Stat 3: Safe items
SELECT COUNT(*) as "Safe (> 7 days)"
FROM inventory_items
WHERE (julianday(expiry_date) - julianday(COALESCE((SELECT value FROM system_config WHERE key = 'simulated_date'), date('now'))) > 7 OR expiry_date IS NULL)
  AND status = 'ACTIVE';
```
**Purpose:** At-a-glance triage status with Red/Yellow/Green stat panels.

#### Panel 3: 🍳 AI Recipe Suggestions (Table)
**Type:** Table
**SQL:**
```sql
SELECT
    r.title as "Recipe",
    r.ingredient_names as "Uses Expiring Items",
    r.estimated_servings as "Servings",
    ROUND(r.co2_saved_kg, 1) as "CO₂ Saved (kg)",
    CASE WHEN r.ai_generated = 1 THEN '🤖 AI' ELSE '📋 Rule-based' END as "Source",
    r.created_at as "Generated"
FROM recipes r
ORDER BY r.created_at DESC
LIMIT 5
```
**Purpose:** Shows the latest AI-generated recipes for expiring ingredients. Judges see AI applied to waste reduction.

#### Panel 4: 📈 Burn-Rate Forecast (Time Series)
**Type:** Time series graph
**SQL:**
```sql
-- Historical usage (actual)
SELECT
    date(e.timestamp) as time,
    SUM(ABS(e.qty_change)) as "Daily Usage"
FROM inventory_events e
WHERE e.action_type = 'USE'
  AND e.item_id = '${item_id}'  -- Variable selector
GROUP BY date(e.timestamp)
ORDER BY time
```
```sql
-- Predicted run-out overlay
SELECT
    date(f.computed_at) as time,
    f.daily_burn_rate as "Predicted Burn Rate",
    f.days_of_supply as "Days of Supply"
FROM forecasts f
WHERE f.item_id = '${item_id}'
ORDER BY f.computed_at DESC
LIMIT 1
```
**Purpose:** Historical usage line with predicted future line. Shows deterministic math over AI.

#### Panel 5: 🌍 Carbon Impact Dashboard (Stat + Bar)
**Type:** Stat panel + Bar chart
**SQL (Total CO₂ Saved):**
```sql
SELECT
    ROUND(SUM(r.co2_saved_kg), 1) as "Total CO₂ Saved (kg)"
FROM recipes r
WHERE r.co2_saved_kg > 0;
```
**SQL (CO₂ by Category):**
```sql
SELECT
    i.category,
    ROUND(SUM(i.quantity * i.co2_per_unit_kg), 1) as "CO₂ Footprint (kg)"
FROM inventory_items i
WHERE i.status IN ('CONSUMED', 'DONATED')
GROUP BY i.category
ORDER BY "CO₂ Footprint (kg)" DESC
```
**Purpose:** Carbon impact tracking — shows sustainability metric directly.

#### Panel 6: 📋 Ingestion Activity Log (Table)
**Type:** Table
**SQL:**
```sql
SELECT
    a.timestamp,
    a.input_method as "Input Type",
    a.event_type as "Event",
    CASE
        WHEN a.confidence >= 0.85 THEN '✅ ' || ROUND(a.confidence * 100) || '%'
        WHEN a.confidence IS NOT NULL THEN '⚠️ ' || ROUND(a.confidence * 100) || '%'
        ELSE '—'
    END as "Confidence",
    a.latency_ms || 'ms' as "Latency",
    a.model_used as "Model",
    SUBSTR(a.details, 1, 100) as "Details"
FROM audit_log a
WHERE a.event_type IN ('INGESTION', 'AI_CALL', 'AI_FALLBACK')
ORDER BY a.timestamp DESC
LIMIT 20
```
**Purpose:** Recent activity feed showing input types, confidence scores, and latencies.

#### Panel 7: 🤖 AI Health & Fallback Monitor (Pie + Stat)
**Type:** Pie chart + Stats
**SQL (Pie - AI Success vs Fallback vs Bypass):**
```sql
SELECT
    CASE
        WHEN event_type = 'AI_CALL' AND severity = 'INFO' THEN 'AI Success'
        WHEN event_type = 'AI_FALLBACK' THEN 'AI Fallback'
        WHEN event_type = 'AI_BYPASSED' THEN 'AI Bypassed'
    END as "Status",
    COUNT(*) as "Count"
FROM audit_log
WHERE event_type IN ('AI_CALL', 'AI_FALLBACK', 'AI_BYPASSED')
GROUP BY "Status"
```
**SQL (Stat - Fallback Rate):**
```sql
SELECT
    ROUND(
        CAST(SUM(CASE WHEN event_type IN ('AI_FALLBACK', 'AI_BYPASSED') THEN 1 ELSE 0 END) AS FLOAT) /
        NULLIF(COUNT(*), 0) * 100, 1
    ) as "Fallback Rate (%)"
FROM audit_log
WHERE event_type IN ('AI_CALL', 'AI_FALLBACK', 'AI_BYPASSED')
```
**Purpose:** Shows judges the fallback engineering in action. Visualizes AI reliability.

#### Panel 8: 👁️ Pending Human Review Queue (Table)
**Type:** Table
**SQL:**
```sql
SELECT
    p.created_at as "Flagged At",
    p.suggested_item_name as "Suggested Item",
    p.suggested_quantity as "Qty",
    ROUND(p.confidence_score * 100) || '%' as "Confidence",
    p.failure_reason as "Reason",
    CASE p.reviewed
        WHEN 0 THEN '⏳ Pending'
        WHEN 1 THEN '✅ Approved'
        WHEN 2 THEN '❌ Rejected'
    END as "Status"
FROM pending_human_review p
ORDER BY p.reviewed ASC, p.created_at DESC
```
**Purpose:** Shows the hallucination-handling pipeline — items that AI wasn't confident about.

#### Panel 9: 🏆 Waste Prevention Score (Gauge)
**Type:** Gauge panel
**SQL:**
```sql
SELECT
    ROUND(
        (CAST(consumed_before_expiry AS FLOAT) / NULLIF(total_items, 0)) * 100, 1
    ) as "Waste Prevention Score (%)"
FROM (
    SELECT
        COUNT(CASE WHEN status IN ('CONSUMED', 'DONATED') THEN 1 END) as consumed_before_expiry,
        COUNT(*) as total_items
    FROM inventory_items
    WHERE expiry_date IS NOT NULL
)
```
**Purpose:** Single composite metric — what % of perishable items were consumed/donated before expiring.

#### Panel 10: 📅 Forecast Accuracy & Annotations (Time Series)
**Type:** Time series with Grafana annotations
**SQL:**
```sql
SELECT
    date(e.timestamp) as time,
    SUM(CASE WHEN e.action_type = 'USE' THEN ABS(e.qty_change) ELSE 0 END) as "Actual Usage",
    SUM(CASE WHEN e.action_type = 'ADD' OR e.action_type = 'RESTOCK' THEN e.qty_change ELSE 0 END) as "Restocks"
FROM inventory_events e
GROUP BY date(e.timestamp)
ORDER BY time
```
**Annotations SQL (AI Events):**
```sql
SELECT
    a.timestamp as time,
    a.event_type || ': ' || SUBSTR(a.details, 1, 50) as text,
    CASE a.severity
        WHEN 'ERROR' THEN 'red'
        WHEN 'WARN' THEN 'yellow'
        ELSE 'green'
    END as color
FROM audit_log a
WHERE a.event_type IN ('AI_BYPASSED', 'AI_FALLBACK', 'TRIAGE')
ORDER BY a.timestamp DESC
```
**Purpose:** Time series with AI event annotations overlaid — visual audit trail. Shows when AI failed and fallbacks triggered.

### Grafana Annotations for AI Events

Annotations are added programmatically when AI events occur:
```python
async def add_grafana_annotation(event_type: str, text: str, tags: list[str]):
    """Add an annotation to the Grafana dashboard timeline."""
    # Write to audit_log table — Grafana reads via annotation SQL query
    await log_audit(event_type, details={"annotation_text": text, "tags": tags})
```

No separate Grafana API call needed — we use Grafana's "SQL annotation query" feature that reads from our `audit_log` table directly.

---

## 11. Synthetic Datasets

### Dataset 1: `carbon_impact_db.csv` (Lookup Table — ~30 items)

CO₂ values sourced from **Our World in Data** published per-kg emissions for common food categories.

| item_name | category | co2_per_unit_kg | avg_shelf_life_days | preferred_partner |
|---|---|---|---|---|
| whole milk | Milk & Cream | 3.2 | 7 | FoodRescue Local |
| cheddar cheese | Cheese | 13.5 | 30 | FoodRescue Local |
| greek yogurt | Yogurt | 3.5 | 14 | FoodRescue Local |
| butter | Butter & Spreads | 12.1 | 60 | N/A |
| egg | Eggs | 0.35 | 28 | FoodRescue Local |
| organic apple | Fresh Fruit | 0.4 | 21 | Community Garden |
| banana | Fresh Fruit | 0.7 | 7 | Community Garden |
| tomato | Fresh Vegetables | 1.4 | 10 | Community Garden |
| lettuce | Herbs & Leafy Greens | 0.3 | 5 | Community Garden |
| carrot | Root Vegetables | 0.3 | 21 | Community Garden |
| chicken breast | Poultry | 6.9 | 3 | Food Bank Central |
| ground beef | Red Meat | 27.0 | 3 | Food Bank Central |
| salmon fillet | Seafood | 5.1 | 2 | Food Bank Central |
| sourdough bread | Bread & Rolls | 0.9 | 5 | Shelter Network |
| croissant | Pastry & Cakes | 1.3 | 3 | Shelter Network |
| bagel | Bread & Rolls | 0.8 | 4 | Shelter Network |
| orange juice | Juice & Soft Drinks | 0.7 | 10 | N/A |
| coffee bean | Coffee & Tea | 8.0 | 180 | N/A |
| oat milk | Plant-Based Milk | 0.9 | 14 | N/A |
| white rice | Grains & Rice | 2.7 | 365 | N/A |
| pasta | Pasta & Noodles | 0.9 | 365 | N/A |
| olive oil | Cooking Oils & Vinegar | 3.3 | 365 | N/A |
| printer paper | Office - Paper | 1.1 | 0 | N/A |
| cleaning spray | Cleaning Products | 0.5 | 365 | N/A |
| hand sanitizer | Cleaning Products | 0.3 | 730 | N/A |
| lab ethanol | Lab Chemicals | 2.0 | 365 | University Recycle |
| petri dish | Lab Equipment | 0.8 | 0 | N/A |
| whiteboard marker | Office - Supplies | 0.2 | 180 | N/A |
| napkin | Office - Paper | 0.4 | 0 | N/A |
| sugar | Sugar & Sweeteners | 0.8 | 730 | N/A |

### Dataset 2: `mock_inventory_events.csv` (Time-Series — ~500 rows)

**Generation Strategy:**
- 30 days of history (4 weeks + 2 days)
- ~10-20 events per day
- Weekend spikes: 1.5-2x more consumption events on Sat/Sun
- Realistic patterns: Morning coffee rush, afternoon restocks, end-of-day waste
- Mix of action types: USE (70%), ADD (15%), RESTOCK (10%), WASTE (5%)

**Schema:**
| event_id | timestamp | item_id | item_name | action_type | qty_change | day_of_week | is_weekend | notes |
|---|---|---|---|---|---|---|---|---|
| 1 | 2026-02-17 08:00:00 | milk-001 | whole milk | USE | -2.0 | 1 | 0 | Morning coffee rush |
| 2 | 2026-02-17 08:30:00 | coffee-001 | coffee bean | USE | -0.5 | 1 | 0 | Espresso prep |
| 3 | 2026-02-17 14:00:00 | milk-001 | whole milk | RESTOCK | +20.0 | 1 | 0 | Weekly delivery |
| ... | ... | ... | ... | ... | ... | ... | ... | ... |

**Generation Script:** `scripts/generate_synthetic_data.py`
- Uses `numpy.random` with seed for reproducibility
- Weekend multiplier: 1.6x for cafe items
- Injects some WASTE events for items that "expired"
- Adds realistic notes from a pool of ~20 templates

---

## 12. Docker Setup

### `docker-compose.yml`

```yaml
services:
  app:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: ecopulse-app
    ports:
      - "8000:8000"
    volumes:
      - ecopulse-data:/data            # SQLite DB lives here
      - ./data:/app/data:ro            # Synthetic CSVs (read-only)
      - ./sample_inputs:/app/samples:ro # Sample receipt images, audio files
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - DATABASE_PATH=/data/ecopulse.db
      - CONFIDENCE_THRESHOLD=0.85
      - LLM_TIMEOUT_SECONDS=60
      - MODEL_NAME=gemini-2.5-flash
      - DEV_MODE=true
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    restart: unless-stopped

  grafana:
    image: grafana/grafana-oss:latest
    container_name: ecopulse-grafana
    ports:
      - "3000:3000"
    volumes:
      - ecopulse-data:/data:ro                          # Read-only access to SQLite
      - ./grafana/provisioning:/etc/grafana/provisioning # Auto-load dashboards
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=ecopulse
      - GF_INSTALL_PLUGINS=frser-sqlite-datasource      # Auto-install SQLite plugin
      - GF_DASHBOARDS_DEFAULT_HOME_DASHBOARD_PATH=/etc/grafana/provisioning/dashboards/eco-pulse.json
    depends_on:
      app:
        condition: service_healthy
    restart: unless-stopped

volumes:
  ecopulse-data:
    driver: local
```

### `backend/Dockerfile`

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for audio processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libportaudio2 \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p /data

# Expose port
EXPOSE 8000

# Default command: run FastAPI server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### `backend/requirements.txt`

```
# Web Framework
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
python-multipart>=0.0.9

# Database
sqlalchemy>=2.0
aiosqlite>=0.20.0

# AI
google-genai>=1.0.0

# Data Validation
pydantic>=2.0
pydantic-settings>=2.0

# Forecasting
scikit-learn>=1.5.0
numpy>=1.26.0

# CLI
typer>=0.12.0
rich>=13.0

# Audio
sounddevice>=0.5.0
soundfile>=0.12.0

# Testing
pytest>=8.0
pytest-asyncio>=0.23.0
pytest-mock>=3.14.0
httpx>=0.27.0  # For FastAPI TestClient async

# Utilities
python-dotenv>=1.0.0
```

### One-Command Launch

```bash
# Clone and run
git clone https://github.com/<user>/eco-pulse.git
cd eco-pulse
echo "GEMINI_API_KEY=your-key-here" > .env
docker compose up -d

# Use the CLI
docker exec -it ecopulse-app python -m cli --help

# Or use the API
curl http://localhost:8000/docs

# Open Grafana
open http://localhost:3000  # admin/ecopulse
```

---

## 13. Testing Strategy — Comprehensive

### Test Files & Coverage

| Test File | Tests | What It Validates |
|---|---|---|
| `test_ingestion_fallbacks.py` | 7 tests | Low confidence routing, Pydantic validation retry + failure, empty response retry + manual fallback |
| `test_timeout_and_ratelimit.py` | 5 tests | API timeout → human review (no auto-discount), rate limit → wait + retry + user notification, API error → notify + human review, audit trail |
| `test_math_forecasting.py` | 4 tests | Linear regression accuracy, insufficient data handling, day-of-week features, weekend multiplier |
| `test_carbon_lookup.py` | 2 tests | Known item lookup, unknown item → AI lookup + table update |
| `test_normalizer.py` | 5 tests | Name normalization (plurals, spelling), unit conversion, pack-size resolution, dedup exact match, dedup fuzzy match |

### Detailed Test Implementations

#### `test_ingestion_fallbacks.py`

```python
import pytest
from unittest.mock import patch, AsyncMock
from backend.ai_service import process_input, ExtractionResult, ExtractedItem

@pytest.mark.asyncio
async def test_low_confidence_routes_to_pending_queue():
    """F1: LLM returns confidence < 85% → item goes to pending_human_review."""
    mock_result = ExtractionResult(
        items=[ExtractedItem(
            item_name="Milk", quantity=10, unit="L",
            category="Milk & Cream", confidence_score=0.65,
            expiry_date="2026-03-25"
        )],
        source_description="Blurry receipt"
    )

    with patch('backend.ai_service.call_gemini', new_callable=AsyncMock, return_value=mock_result):
        result = await process_input("fake_receipt.jpg", input_method="IMAGE")

        assert result.items_added_to_inventory == 0
        assert result.items_sent_to_review == 1
        assert result.review_reasons[0] == "LOW_CONFIDENCE"

@pytest.mark.asyncio
async def test_pydantic_validation_retries_once_with_error():
    """F2: LLM returns bad JSON → retry with error context → success on retry."""
    good_result = ExtractionResult(
        items=[ExtractedItem(item_name="Milk", quantity=10, unit="L",
                             category="Milk & Cream", confidence_score=0.92,
                             expiry_date="2026-03-25")],
        source_description="Retry succeeded"
    )

    with patch('backend.ai_service.call_gemini', new_callable=AsyncMock,
               side_effect=[ValueError("Invalid JSON"), good_result]):
        result = await process_input("messy_receipt.jpg", input_method="IMAGE")

        assert result.items_added_to_inventory == 1  # Retry succeeded
        assert result.retry_count == 1

@pytest.mark.asyncio
async def test_pydantic_validation_exhausts_retries_routes_to_pending():
    """F2: LLM fails validation on both attempts → routes to pending review."""
    with patch('backend.ai_service.call_gemini', new_callable=AsyncMock,
               side_effect=ValueError("Invalid JSON from LLM")):
        result = await process_input("messy_receipt.jpg", input_method="IMAGE")

        assert result.items_sent_to_review == 1
        assert result.review_reasons[0] == "VALIDATION_FAILED"
        assert result.retry_count == 1  # Confirms retry was attempted

@pytest.mark.asyncio
async def test_high_confidence_routes_to_active_inventory():
    """Happy path: LLM returns confidence >= 85% → active inventory."""
    mock_result = ExtractionResult(
        items=[ExtractedItem(
            item_name="Organic Apples", quantity=50, unit="units",
            category="Fresh Fruit", confidence_score=0.94,
            expiry_date="2026-03-28"
        )],
        source_description="Clear receipt photo"
    )

    with patch('backend.ai_service.call_gemini', new_callable=AsyncMock, return_value=mock_result):
        result = await process_input("clear_receipt.jpg", input_method="IMAGE")

        assert result.items_added_to_inventory == 1
        assert result.items_sent_to_review == 0

@pytest.mark.asyncio
async def test_mixed_confidence_splits_correctly():
    """Some items high confidence, some low → split routing."""
    mock_result = ExtractionResult(
        items=[
            ExtractedItem(item_name="Milk", quantity=10, unit="L",
                         category="Milk & Cream", confidence_score=0.92, expiry_date="2026-03-25"),
            ExtractedItem(item_name="Unknown Item", quantity=5, unit="units",
                         category="Other", confidence_score=0.45, expiry_date=None),
        ],
        source_description="Partially readable receipt"
    )

    with patch('backend.ai_service.call_gemini', new_callable=AsyncMock, return_value=mock_result):
        result = await process_input("partial_receipt.jpg", input_method="IMAGE")

        assert result.items_added_to_inventory == 1
        assert result.items_sent_to_review == 1

@pytest.mark.asyncio
async def test_empty_extraction_retries_then_triggers_manual():
    """F5: LLM returns zero items → retry with rephrased prompt → still empty → manual entry."""
    mock_result = ExtractionResult(items=[], source_description="Unreadable input")

    with patch('backend.ai_service.call_gemini', new_callable=AsyncMock, return_value=mock_result):
        result = await process_input("blank_image.jpg", input_method="IMAGE")

        assert result.items_added_to_inventory == 0
        assert result.fallback_triggered == "EMPTY_RESPONSE"
        assert result.retry_count == 1  # Confirms retry was attempted before manual

@pytest.mark.asyncio
async def test_empty_extraction_retry_succeeds():
    """F5: LLM returns zero items first try → retry finds items → success."""
    empty_result = ExtractionResult(items=[], source_description="Nothing found")
    retry_result = ExtractionResult(
        items=[ExtractedItem(item_name="Apples", quantity=5, unit="units",
                             category="Fresh Fruit", confidence_score=0.88,
                             expiry_date="2026-03-28")],
        source_description="Found on retry"
    )

    with patch('backend.ai_service.call_gemini', new_callable=AsyncMock,
               side_effect=[empty_result, retry_result]):
        result = await process_input("dim_photo.jpg", input_method="IMAGE")

        assert result.items_added_to_inventory == 1
        assert result.retry_count == 1
```

#### `test_timeout_and_ratelimit.py`

```python
import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from backend.ai_service import triage_expiring_item, call_gemini_with_rate_limit_handling
import google.api_core.exceptions

@pytest.mark.asyncio
async def test_llm_timeout_routes_to_human_review():
    """F3: LLM times out (60s) → item routed to human review, NO auto-discount."""
    with patch('backend.ai_service.call_gemini', new_callable=AsyncMock,
               side_effect=asyncio.TimeoutError):
        result = await triage_expiring_item(item_id="milk-001")

        assert result.action_taken == "PENDING_HUMAN_REVIEW"
        assert result.ai_bypassed == True
        assert result.ai_generated == False
        # Crucially: no auto-discount applied
        assert result.action_taken != "AUTO_DISCOUNT_50"

@pytest.mark.asyncio
async def test_rate_limit_waits_and_retries_successfully():
    """F4: Rate limited (429) → wait Retry-After seconds → retry succeeds."""
    rate_limit_error = google.api_core.exceptions.ResourceExhausted("429 Rate limit")
    rate_limit_error.retry_after = 2  # 2 seconds for test speed

    good_result = ExtractionResult(
        items=[ExtractedItem(item_name="Milk", quantity=10, unit="L",
                             category="Milk & Cream", confidence_score=0.92)],
        source_description="Success after rate limit"
    )
    notifications = []

    with patch('backend.ai_service.call_gemini', new_callable=AsyncMock,
               side_effect=[rate_limit_error, good_result]):
        result = await call_gemini_with_rate_limit_handling(
            contents=["test"], schema={},
            notify_callback=lambda msg: notifications.append(msg)
        )

        assert len(result.items) == 1
        assert any("rate limit" in n.lower() for n in notifications)
        assert any("Retry successful" in n for n in notifications)

@pytest.mark.asyncio
async def test_rate_limit_retry_fails_routes_to_review():
    """F4: Rate limited → retry also fails → routes to human review."""
    rate_limit_error = google.api_core.exceptions.ResourceExhausted("429")
    rate_limit_error.retry_after = 1

    notifications = []

    with patch('backend.ai_service.call_gemini', new_callable=AsyncMock,
               side_effect=rate_limit_error):  # Fails both times
        with pytest.raises(Exception):
            await call_gemini_with_rate_limit_handling(
                contents=["test"], schema={},
                notify_callback=lambda msg: notifications.append(msg)
            )

        assert any("Retry failed" in n for n in notifications)

@pytest.mark.asyncio
async def test_api_error_notifies_user_and_routes_to_review():
    """F4b: API connection error → user notified → item to human review."""
    notifications = []

    with patch('backend.ai_service.call_gemini', new_callable=AsyncMock,
               side_effect=ConnectionError("API unreachable")):
        with pytest.raises(ConnectionError):
            await call_gemini_with_rate_limit_handling(
                contents=["test"], schema={},
                notify_callback=lambda msg: notifications.append(msg)
            )

        assert any("connection failed" in n.lower() for n in notifications)

@pytest.mark.asyncio
async def test_timeout_creates_human_review_audit_trail():
    """Verify audit log entry routes to human review on timeout."""
    with patch('backend.ai_service.call_gemini', new_callable=AsyncMock,
               side_effect=asyncio.TimeoutError):
        result = await triage_expiring_item(item_id="milk-001")

        logs = await get_audit_logs(event_type="AI_FALLBACK")
        assert len(logs) >= 1
        assert logs[-1]["severity"] == "WARN"
        assert "TIMEOUT" in logs[-1]["details"]
        assert "HUMAN_REVIEW" in logs[-1]["details"]
```

#### `test_math_forecasting.py`

```python
import pytest
import numpy as np
from datetime import datetime, timedelta
from backend.predictive_math import forecast_burn_rate

@pytest.mark.asyncio
async def test_basic_linear_forecast():
    """Happy path: sufficient data → accurate prediction."""
    # Create 14 days of steady 2 units/day consumption
    events = generate_mock_events(item_id="milk-001", daily_rate=2.0, days=14)

    result = await forecast_burn_rate("milk-001", events=events, current_stock=10.0)

    assert result["status"] == "OK"
    assert 4.0 <= result["days_of_supply"] <= 6.0  # ~5 days at 2/day
    assert result["r_squared"] >= 0.5

@pytest.mark.asyncio
async def test_insufficient_data_returns_none():
    """< 7 days of data → returns INSUFFICIENT_DATA status."""
    events = generate_mock_events(item_id="milk-001", daily_rate=2.0, days=3)

    result = await forecast_burn_rate("milk-001", events=events, current_stock=10.0)

    assert result["status"] == "INSUFFICIENT_DATA"
    assert result["days_of_supply"] is None

@pytest.mark.asyncio
async def test_weekend_spike_detected():
    """Weekend consumption is higher → weekend_multiplier > 1.0."""
    # Create events where weekends have 2x consumption
    events = generate_mock_events_with_weekend_spike(
        item_id="coffee-001", weekday_rate=3.0, weekend_rate=6.0, days=21
    )

    result = await forecast_burn_rate("coffee-001", events=events, current_stock=30.0)

    assert result["status"] == "OK"
    assert result["weekend_multiplier"] >= 1.5  # Should detect the spike

@pytest.mark.asyncio
async def test_zero_consumption_infinite_supply():
    """If nothing is consumed → infinite days of supply."""
    events = generate_mock_events(item_id="paper-001", daily_rate=0.0, days=14)

    result = await forecast_burn_rate("paper-001", events=events, current_stock=100.0)

    assert result["days_of_supply"] == float('inf') or result["days_of_supply"] > 300
```

#### `test_normalizer.py`

```python
import pytest
from backend.normalizer import (
    normalize_item_name,
    normalize_quantity_and_unit,
    auto_upscale_unit,
    singularize,
)

def test_name_normalization_plurals_and_casing():
    """Plural forms, mixed case, extra whitespace → canonical singular lowercase."""
    assert normalize_item_name("Apples") == "apple"
    assert normalize_item_name("  ORGANIC  Apples  ") == "organic apple"
    assert normalize_item_name("Tomatoes") == "tomato"
    assert normalize_item_name("Berries") == "berry"
    assert normalize_item_name("Boxes") == "box"

def test_name_normalization_spelling_variants():
    """British → US English spelling normalization."""
    assert normalize_item_name("aluminium foil") == "aluminum foil"
    assert normalize_item_name("Yoghurt") == "yogurt"
    assert normalize_item_name("natural flavour yoghurt") == "natural flavor yogurt"

def test_unit_conversion_known_units():
    """Common cooking/imperial units → canonical metric units."""
    qty, unit = normalize_quantity_and_unit(1, "cup", "rice")
    assert unit == "mL"
    assert qty == 240

    qty, unit = normalize_quantity_and_unit(2, "lbs", "chicken")
    assert unit == "g"
    assert qty == 907.2

    qty, unit = normalize_quantity_and_unit(1, "gallon", "milk")
    assert unit == "L"
    assert qty == 3.785

    qty, unit = normalize_quantity_and_unit(1, "dozen", "egg")
    assert unit == "units"
    assert qty == 12

def test_pack_size_resolution():
    """Ambiguous 'packs' → resolved via DEFAULT_PACK_SIZES table."""
    qty, unit = normalize_quantity_and_unit(2, "packs", "rice")
    assert unit == "g"
    assert qty == 2000  # 2 packs × 1000g

    qty, unit = normalize_quantity_and_unit(1, "pack", "butter")
    assert unit == "g"
    assert qty == 250

    # Unknown pack size → falls back to units
    qty, unit = normalize_quantity_and_unit(3, "packs", "mystery item")
    assert unit == "units"
    assert qty == 3

def test_auto_upscale():
    """Large sub-units get upscaled for readability."""
    qty, unit = auto_upscale_unit(1500, "g")
    assert qty == 1.5
    assert unit == "kg"

    qty, unit = auto_upscale_unit(2000, "mL")
    assert qty == 2.0
    assert unit == "L"

    # Below threshold → no change
    qty, unit = auto_upscale_unit(500, "g")
    assert qty == 500
    assert unit == "g"
```

#### `tests/conftest.py` (Shared Test Fixtures)

```python
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from backend.database import Base, get_db
from backend.config import Settings
from backend.schemas import ExtractionResult, ExtractedItem


@pytest_asyncio.fixture
async def test_db():
    """In-memory SQLite database for testing. Creates all tables, yields session, tears down."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSession(engine) as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
def mock_gemini_client():
    """Mock Gemini API client with configurable responses."""
    client = MagicMock()
    client.models.generate_content = AsyncMock()
    return client


@pytest.fixture
def sample_extraction_result():
    """Sample successful extraction result for testing."""
    return ExtractionResult(
        items=[
            ExtractedItem(
                item_name="whole milk", quantity=10, unit="L",
                category="Milk & Cream", confidence_score=0.94,
                expiry_date="2026-03-25", raw_input_text="10L whole milk"
            ),
            ExtractedItem(
                item_name="organic apple", quantity=50, unit="units",
                category="Fresh Fruit", confidence_score=0.91,
                expiry_date="2026-03-28", raw_input_text="50 organic apples"
            ),
        ],
        source_description="Test receipt"
    )


@pytest.fixture
def test_settings():
    """Test settings with defaults — uses a fake API key."""
    return Settings(
        gemini_api_key="test-key-not-real",
        model_name="gemini-2.5-flash",
        confidence_threshold=0.85,
        llm_timeout_seconds=60,
        database_path=":memory:",
        dev_mode=True,
    )


@pytest_asyncio.fixture
async def seeded_db(test_db):
    """
    Database pre-loaded with sample inventory and events for testing.
    - Inserts ~10 inventory items from the carbon_impact_db
    - Inserts 14+ days of mock usage events for forecasting tests
    - Inserts carbon_impact_db entries for carbon lookup tests
    """
    # Implementation: Load sample data into test_db
    # ... (insert sample inventory items, usage events, carbon entries)
    yield test_db
```

---

## 14. Developer Mode — Time Simulation

### Purpose
The company FAQ explicitly allows "Developer Mode" to simulate time passing. This is critical for demonstrating:
- Items approaching expiry
- Triage triggers firing
- Forecasts updating
- Grafana dashboards reflecting urgency changes

### Implementation

```python
from datetime import datetime, timedelta

async def get_current_date() -> datetime:
    """
    Returns the current date, reading the simulated date from the system_config table.
    Falls back to real current date if no simulation is active.
    This ensures both Python code AND Grafana queries see the same simulated date
    (Grafana reads from the same system_config table via SQL).
    """
    simulated = await db.get_config("simulated_date")
    if simulated:
        return datetime.fromisoformat(simulated)
    return datetime.now()

async def advance_time(days: int):
    """
    Simulate time passing by N days.
    - Persists the new simulated date to system_config (so Grafana sees it too)
    - Recalculates expiry status for all items
    - Triggers triage for newly-expiring items
    - Regenerates forecasts
    """
    current = await get_current_date()
    new_date = current + timedelta(days=days)

    # Persist to system_config — Grafana queries will pick this up automatically
    await db.set_config("simulated_date", new_date.date().isoformat())

    # Update expiry calculations
    await recalculate_expiry_status()

    # Auto-trigger triage for items now in the danger zone
    expiring = await db.get_items_expiring_within(days=3)
    for item in expiring:
        await triage_expiring_item(item["id"])

    # Refresh forecasts
    await update_all_forecasts()

    await log_audit("DEV_TIME_ADVANCE", details={"days_advanced": days,
                    "new_simulated_date": new_date.date().isoformat()})
```

### CLI Usage

```bash
# Advance 5 days — items that were "safe" now become "urgent"
docker exec -it ecopulse-app python -m cli dev advance-time --days 5

# Output:
# ⏩ Time advanced by 5 days. Simulated date: 2026-03-24
# 🚨 3 items now in triage zone (< 3 days to expiry)
# 🍳 2 recipes generated for expiring items
# 📈 All forecasts updated
```

---

## 15. Repository Structure

```
eco-pulse/
│
├── backend/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application + startup events
│   ├── cli.py                  # Typer CLI application (the primary interface)
│   ├── ai_service.py           # Gemini API wrappers, prompts, structured output
│   ├── predictive_math.py      # Linear regression with day-of-week features
│   ├── models.py               # SQLAlchemy models (all tables)
│   ├── schemas.py              # Pydantic schemas (request/response + Gemini schemas)
│   ├── database.py             # SQLite async engine, session factory, init
│   ├── normalizer.py           # Input standardization & dedup (name, unit, quantity)
│   ├── carbon_lookup.py        # Green DB lookup + AI fallback for unknown items
│   ├── pii_scrubber.py         # Regex PII removal middleware
│   ├── config.py               # pydantic-settings configuration
│   ├── dev_mode.py             # Time simulation logic
│   ├── requirements.txt
│   └── Dockerfile
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # Shared fixtures (test DB, mock AI, etc.)
│   ├── test_ingestion_fallbacks.py
│   ├── test_timeout_and_ratelimit.py
│   ├── test_math_forecasting.py
│   ├── test_carbon_lookup.py
│   └── test_normalizer.py
│
├── data/
│   ├── carbon_impact_db.csv    # Green DB lookup table (~30 items)
│   ├── mock_inventory_events.csv  # Time-series data (~500 rows)
│   └── README.md               # Data sources and methodology
│
├── scripts/
│   ├── generate_synthetic_data.py  # Reproducible data generation
│   └── seed_database.py            # Load CSVs into SQLite
│
├── sample_inputs/              # Demo files for the video
│   ├── receipt_clear.jpg       # Clear receipt image (high confidence)
│   ├── receipt_blurry.jpg      # Blurry receipt (low confidence → fallback)
│   ├── shelf_photo.jpg         # Pantry shelf photo
│   ├── voice_sample.wav        # Pre-recorded voice sample
│   └── README.md               # Image attribution/sources
│
├── grafana/
│   └── provisioning/
│       ├── datasources/
│       │   └── datasource.yml  # SQLite datasource config
│       └── dashboards/
│           ├── dashboard.yml   # Dashboard provider config
│           └── eco-pulse.json  # Exported dashboard JSON (all 10 panels)
│
├── .env.example                # Template for API keys
├── .gitignore
├── docker-compose.yml
├── README.md                   # Architecture, tradeoffs, setup instructions
└── Demo_Video.mp4              # 5-7 minute screen recording
```

---

## 16. PII Scrubber

### Design Principle
PII scrubbing operates at **two stages** and is entirely **synchronous** (pure regex, no I/O):
1. **Pre-AI (text input only):** Scrub text before sending to the cloud LLM
2. **Pre-DB (all input modes):** Scrub ALL extracted text fields before database storage — ensuring no PII persists in our system regardless of input method

For image and voice inputs, the raw media is sent directly to Gemini — it is the user's responsibility to not photograph/dictate sensitive documents. However, any text extracted by Gemini is scrubbed before it reaches the database.

### Implementation

```python
import re
import logging

logger = logging.getLogger(__name__)

PII_PATTERNS = [
    # Credit card numbers (with spaces, dashes, or no separator)
    (r'\b(?:\d{4}[-\s]?){3}\d{4}\b', '[REDACTED_CARD]'),

    # Phone numbers (US format variants)
    (r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b', '[REDACTED_PHONE]'),

    # Email addresses
    (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[REDACTED_EMAIL]'),

    # SSN (US)
    (r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b', '[REDACTED_SSN]'),
]


def scrub_pii(text: str) -> str:
    """
    Synchronous PII scrubber. Removes PII patterns from text via regex.
    Used pre-AI for text input and pre-DB for all extracted fields.
    Returns the scrubbed text.
    """
    redaction_count = 0
    scrubbed = text

    for pattern, replacement in PII_PATTERNS:
        matches = re.findall(pattern, scrubbed)
        if matches:
            redaction_count += len(matches)
            scrubbed = re.sub(pattern, replacement, scrubbed)

    if redaction_count > 0:
        # Sync logging — PII scrubbing must not depend on async I/O
        logger.info(f"PII_SCRUBBED: {redaction_count} redaction(s) applied")

    return scrubbed


def scrub_extracted_fields(item: dict) -> dict:
    """
    Scrub PII from all text fields of an extracted item before DB storage.
    Applied to ALL input modes (image, voice, text) after Gemini extraction.
    """
    text_fields = ["item_name", "raw_input_text", "source_description"]
    for field in text_fields:
        if field in item and isinstance(item[field], str):
            item[field] = scrub_pii(item[field])
    return item
```

### Where It's Applied
- **Text input (pre-AI):** `scrub_pii()` on raw text before sending to Gemini
- **All input modes (pre-DB):** `scrub_extracted_fields()` on every extracted item before database insertion — catches any PII that Gemini extracted from images/voice
- **Audit trail:** Redaction count logged synchronously via Python's `logging` module

---

## 17. Configuration Management

### Using pydantic-settings

```python
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    # AI Configuration
    gemini_api_key: str = Field(..., description="Google AI Studio API key")
    model_name: str = Field(default="gemini-2.5-flash", description="Gemini model to use")
    confidence_threshold: float = Field(default=0.85, description="Min confidence to accept")
    llm_timeout_seconds: int = Field(default=60, description="Max wait for LLM response")

    # Database
    database_path: str = Field(default="/data/ecopulse.db", description="SQLite DB path")

    # Application
    dev_mode: bool = Field(default=False, description="Enable developer mode features")
    log_level: str = Field(default="INFO", description="Logging level")

    # Grafana (for API annotation calls if needed)
    grafana_url: str = Field(default="http://localhost:3000", description="Grafana URL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()


# Startup validation — fail fast with a clear error message
def validate_settings():
    """
    Called at app startup. Ensures the API key is set and not still
    using the placeholder value from .env.example.
    """
    if not settings.gemini_api_key or settings.gemini_api_key == "your-google-ai-studio-api-key":
        from rich.console import Console
        console = Console()
        console.print("[bold red]❌ GEMINI_API_KEY not set or still using placeholder.[/bold red]")
        console.print("[yellow]Get a free key at: https://ai.google.dev[/yellow]")
        console.print("[yellow]Set it in .env: GEMINI_API_KEY=your-key-here[/yellow]")
        raise SystemExit(1)
```

### `.env.example`

```env
GEMINI_API_KEY=your-google-ai-studio-api-key
MODEL_NAME=gemini-2.5-flash
CONFIDENCE_THRESHOLD=0.85
LLM_TIMEOUT_SECONDS=60
DATABASE_PATH=/data/ecopulse.db
DEV_MODE=true
LOG_LEVEL=INFO
```

---

## 18. Tradeoffs Documentation

*Copy into final README — Tradeoffs section*

### Tradeoff 1: Cloud LLM vs. Local Edge Model
- **Decision:** Cloud LLM (Gemini 2.5 Flash) over local model (Llama-3-8B)
- **Why:** Local model requires ~16GB RAM, adds 4GB+ to Docker image, inference is 10x slower. Cloud Gemini is free-tier, sub-second latency, natively multimodal (text+image+audio in one model).
- **Mitigation:** Two-stage PII scrubbing: (1) Text input is scrubbed via regex before sending to the cloud API. (2) For image and voice inputs, the raw media is sent to Gemini (user's responsibility to avoid photographing sensitive documents), but ALL extracted data from any input mode is PII-scrubbed before database storage — ensuring no PII persists in our system. Audit trail logs all scrub events.

### Tradeoff 2: SQLite vs. PostgreSQL
- **Decision:** SQLite over PostgreSQL
- **Why:** Eliminates an entire Docker container. Zero configuration. No connection strings, no auth, no schema migrations. WAL mode handles concurrent reads (Grafana) and writes (app) at our scale (<100 events/day).
- **Risk:** SQLite doesn't scale to multi-server deployments. Acceptable because our target audience (small cafes/non-profits) runs on a single machine.
- **Grafana:** Connected via the `frser-sqlite-datasource` community plugin, auto-installed on container startup.

### Tradeoff 3: FastAPI BackgroundTasks vs. Celery/Redis
- **Decision:** Built-in BackgroundTasks over Celery+Redis
- **Why:** Celery requires 2 additional containers (Redis broker + Celery worker). Our processing volume (<100 tasks/day) doesn't warrant a full message queue. BackgroundTasks is zero-dependency and built into FastAPI.
- **Limitation:** Tasks don't survive container restarts. Acceptable for a hackathon demo.

### Tradeoff 4: Deterministic Math vs. AI for Forecasting
- **Decision:** scikit-learn LinearRegression over LLM-based prediction
- **Why:** LLMs are notoriously unreliable at arithmetic and time-series tasks. Linear regression is orders of magnitude faster (< 1ms vs. 1-3s), computationally free, and 100% reproducible. We enhanced it with day-of-week features and weekend multipliers for better accuracy.
- **Principle:** Reserve AI for generative tasks (extraction, recipes) where it genuinely excels.

### Tradeoff 5: CLI-First vs. Web UI
- **Decision:** Typer+Rich CLI over building a web frontend
- **Why:** The evaluation criteria explicitly states "CLI is acceptable" and "we score the working product and technical behavior, not presentation polish." A Rich CLI produces beautiful, colorful terminal output that demos exceptionally well in a screen recording. Building a React/Next.js frontend would consume 40%+ of development time for zero additional scoring.

### Tradeoff 6: Gemini 2.5 Flash vs. Gemini 3 Flash Preview
- **Decision:** Gemini 2.5 Flash (stable) over Gemini 3 Flash Preview
- **Why:** Preview models may change without notice, potentially breaking the demo before submission. 2.5 Flash is stable, fully free, and supports all required features (multimodal input, structured output, audio understanding). The model can be swapped via a single environment variable if 3.x becomes stable.

---

## 19. Video Script (Updated — 7 Minutes)

### [0:00 - 0:45] The Hook
**Visual:** README or problem slide
**Audio:** "Small businesses waste up to 15% of their inventory because tracking is tedious. Eco-Pulse is a lightweight, AI-driven inventory engine that runs in two Docker containers — no frontend needed."

### [0:45 - 2:00] Docker Launch + Ease of Entry (Image)
**Visual:** Terminal → `docker compose up -d` → containers start → `eco-pulse ingest --image receipt.jpg`
**Audio:** "One command launches everything. Let's add inventory by simply photographing a receipt. Gemini 2.5 Flash extracts structured data — item names, quantities, expiry dates, categories — all validated by Pydantic schemas. Notice the confidence scores: 94%, 91%, 88%. These passed our 85% threshold and went straight to active inventory."

### [2:00 - 2:45] Voice Input
**Visual:** `eco-pulse ingest --voice --file sample.wav` → structured output
**Audio:** "We support voice input too. In Docker we use the --file flag with a pre-recorded audio sample. The same Gemini model processes audio natively — no separate speech-to-text library needed. One API, all modalities."

### [2:45 - 3:30] The Fallback Demo (Low Confidence)
**Visual:** `eco-pulse ingest --image blurry_receipt.jpg` → show low confidence → item routed to pending review → `eco-pulse inventory review`
**Audio:** "Now watch what happens with a blurry receipt. The AI returns a 62% confidence score — below our 85% threshold. Instead of trusting a hallucination, the system routes it to a human review queue. The dashboard flags it as 'Requires Approval.' This is our first fallback."

### [3:30 - 4:30] Forecasting + Grafana
**Visual:** `eco-pulse forecast` → burn rate table → switch to Grafana dashboards → point out panels
**Audio:** "Our Waste-Zero Engine uses deterministic linear regression — not AI — for burn-rate forecasting. We intentionally chose math over AI because it's faster, cheaper, and 100% reproducible. Notice the weekend multiplier: cafes consume 1.6x more on weekends. The Grafana dashboard shows our expiry triage heatmap, carbon impact tracker, and forecast accuracy."

### [4:30 - 5:30] AI Triage + Recipe Generation
**Visual:** `eco-pulse dev advance-time --days 5` → items become urgent → `eco-pulse triage` → AI recipes generated → Grafana recipe panel
**Audio:** "Let's advance time by 5 days using dev mode. Suddenly, milk and yogurt are expiring tomorrow. The system triggers our AI triage — Gemini generates 'Special of the Day' recipes using these expiring ingredients. The CO₂ saved by cooking instead of trashing is tracked automatically."

### [5:30 - 6:15] The Mic Drop — Breaking the AI
**Visual:** Change API key to invalid → `eco-pulse triage` → fallback fires → item routed to human review queue → audit log shows AI_FALLBACK
**Audio:** "Now the mic drop. I'm deliberately breaking the AI connection. Watch: the system doesn't crash. It catches the error and routes the item to a human review queue — because automated discounts without human oversight would be irresponsible. If we hit a rate limit instead, the system waits, retries automatically, and notifies the user with an ETA. This is production-grade graceful degradation."

### [6:15 - 7:00] Tests + Close
**Visual:** Terminal → `pytest -v` → all green → point out specific test names
**Audio:** "We applied TDD specifically for these fallback scenarios. Notice the test names: low confidence routing, timeout heuristics, PII scrubbing, weekend spike detection. Our main tradeoffs: SQLite over Postgres for simplicity, deterministic math over AI for forecasting, and CLI over web UI for zero-polish maximum-substance. Thank you for watching."

---

## 20. End-to-End Demo Flows

Each flow can be triggered independently via the CLI. These are the "test cases" that demonstrate complete pipelines.

### Flow 1: 📷 Image Ingestion (Happy Path)
```bash
docker exec -it ecopulse-app python -m cli ingest --image /app/samples/receipt_clear.jpg
```
**Expected:** Items extracted, high confidence, added to active inventory, carbon scores attached, Grafana updated.

### Flow 2: 🎙️ Voice Ingestion (Happy Path)
```bash
docker exec -it ecopulse-app python -m cli ingest --voice
# (Uses pre-recorded sample in Docker: /app/samples/voice_sample.wav)
```
**Expected:** Audio processed by Gemini, structured output, items added.

### Flow 3: ✏️ Text Ingestion (Happy Path)
```bash
docker exec -it ecopulse-app python -m cli ingest --text "Received 20 liters of whole milk, expiry March 25th, and 50 organic apples expiring next Friday"
```
**Expected:** Natural language parsed, dates calculated relative to current date, items added.

### Flow 4: ⚠️ Low Confidence Fallback
```bash
docker exec -it ecopulse-app python -m cli ingest --image /app/samples/receipt_blurry.jpg
```
**Expected:** AI returns confidence < 85%, items routed to `pending_human_review`, dashboard flags them.

### Flow 5: ⏱️ API Timeout Fallback
```bash
# Uses dev force-timeout command — internally overrides LLM_TIMEOUT_SECONDS to 0.001
docker exec -it ecopulse-app python -m cli dev force-timeout
```
**Expected:** TimeoutError caught, item routed to `pending_human_review` queue (NO auto-discount), AI_FALLBACK logged with TIMEOUT reason. Human decides the action.

### Flow 5b: 🚦 API Rate Limit Handling
```bash
# Uses dev simulate-rate-limit command — fires rapid AI calls to trigger 429
docker exec -it ecopulse-app python -m cli dev simulate-rate-limit
```
**Expected:** Rate limit detected (429), user notified with ETA, system retries with exponential backoff (up to 3 attempts). If retries succeed → normal flow. If all retries fail → routes to human review with notification.

### Flow 6: 📈 Forecast & Burn-Rate
```bash
docker exec -it ecopulse-app python -m cli forecast
```
**Expected:** All items with sufficient data get burn-rate predictions, weekend multipliers calculated.

### Flow 7: 🍳 AI Recipe Generation
```bash
docker exec -it ecopulse-app python -m cli triage
```
**Expected:** Expiring items found via FEFO, Gemini generates recipes, recipes stored and visible in Grafana.

### Flow 8: ⏩ Dev Mode Time Advancement
```bash
docker exec -it ecopulse-app python -m cli dev advance-time --days 10
docker exec -it ecopulse-app python -m cli triage
```
**Expected:** Items that were "safe" are now "urgent", triage triggers automatically.

### Flow 9: 🔍 Inventory CRUD
```bash
# List
docker exec -it ecopulse-app python -m cli inventory list
# Search
docker exec -it ecopulse-app python -m cli inventory search "milk"
# Update
docker exec -it ecopulse-app python -m cli inventory update <id> --qty 5
# Review pending
docker exec -it ecopulse-app python -m cli inventory review
```
**Expected:** Full CRUD operations with Rich terminal output.

### Flow 10: 🧪 Run All Tests
```bash
docker exec -it ecopulse-app pytest -v
```
**Expected:** All tests pass (6 files, ~21 tests).

---

## 21. Implementation Checklist

### Phase 1: Foundation
- [ ] Create repository structure (all directories and empty files)
- [ ] Write `docker-compose.yml` (app + grafana containers)
- [ ] Write `Dockerfile`
- [ ] Write `requirements.txt`
- [ ] Write `config.py` (pydantic-settings)
- [ ] Write `database.py` (SQLAlchemy async + SQLite WAL)
- [ ] Write `models.py` (all 9 tables as SQLAlchemy models, including `system_config`)
- [ ] Write `schemas.py` (all Pydantic schemas)
- [ ] Create database indexes (6 indexes for performance)
- [ ] Create `.env.example`
- [ ] Create `.gitignore`

### Phase 2: Data
- [ ] Write `scripts/generate_synthetic_data.py`
- [ ] Generate `data/carbon_impact_db.csv` (30 items)
- [ ] Generate `data/mock_inventory_events.csv` (500 rows)
- [ ] Write `scripts/seed_database.py` (load CSVs → SQLite)

### Phase 3: Core Backend
- [ ] Write `main.py` (FastAPI app, all endpoints, startup events, `validate_settings()` call)
- [ ] Write `normalizer.py` (name normalization, unit conversion, DB dedup, `convert_to_target_unit()`)
- [ ] Write `carbon_lookup.py` (Green DB lookup + AI fallback for unknown items)
- [ ] Write `pii_scrubber.py` (sync regex PII removal — `scrub_pii()` + `scrub_extracted_fields()`)
- [ ] Write `dev_mode.py` (time simulation via `system_config` table)

### Phase 4: AI Integration
- [ ] Write `ai_service.py` (Gemini wrapper, all 3 input modes)
- [ ] Implement image extraction pipeline
- [ ] Implement voice extraction pipeline
- [ ] Implement text extraction pipeline
- [ ] Implement recipe generation pipeline
- [ ] Implement all 5 fallback paths
- [ ] Implement community mesh stub

### Phase 5: Forecasting
- [ ] Write `predictive_math.py` (linear regression + day-of-week features)
- [ ] Implement `forecast_scheduler()` as asyncio periodic task on FastAPI startup
- [ ] Implement FEFO ordering in triage queries

### Phase 6: CLI
- [ ] Write `cli.py` (Typer app, all commands)
- [ ] Implement `ingest` command (image, voice, text, csv)
- [ ] Implement `inventory` commands (list, search, update, review)
- [ ] Implement `triage` command (with --dry-run)
- [ ] Implement `forecast` command
- [ ] Implement `dev` commands (advance-time, seed-data, reset-db, force-timeout, simulate-rate-limit)
- [ ] Implement `health` command
- [ ] Implement `dashboard` command (opens browser)

### Phase 7: Testing
- [ ] Write `tests/conftest.py` (shared fixtures)
- [ ] Write `test_ingestion_fallbacks.py` (7 tests)
- [ ] Write `test_timeout_and_ratelimit.py` (5 tests)
- [ ] Write `test_math_forecasting.py` (4 tests)
- [ ] Write `test_carbon_lookup.py` (2 tests)
- [ ] Write `test_normalizer.py` (5 tests)
- [ ] Ensure all tests pass in Docker

### Phase 8: Grafana
- [ ] Write `grafana/provisioning/datasources/datasource.yml`
- [ ] Write `grafana/provisioning/dashboards/dashboard.yml`
- [ ] Build all 10 panels in Grafana UI
- [ ] Configure annotation queries for AI events
- [ ] Export dashboard JSON → `grafana/provisioning/dashboards/eco-pulse.json`

### Phase 9: Sample Inputs
- [ ] Source/create `sample_inputs/receipt_clear.jpg` (AI-generated or CC0)
- [ ] Source/create `sample_inputs/receipt_blurry.jpg` (intentionally blurry)
- [ ] Source/create `sample_inputs/shelf_photo.jpg` (pantry shelf)
- [ ] Record `sample_inputs/voice_sample.wav` (inventory dictation)
- [ ] Write attribution notes in `sample_inputs/README.md`

### Phase 10: Documentation & Video
- [ ] Write `README.md` using provided template
- [ ] Include architecture diagram (ASCII or image)
- [ ] Include tradeoffs section
- [ ] Include setup instructions
- [ ] Record 5-7 minute demo video
- [ ] Final review: all checklist items complete

---

## Appendix A: Carbon Footprint Data Sources 
NOTE: the retrieval from these data sources was done by the LLM, the app does no such scraping internally.

| Source | URL | License | Usage |
|---|---|---|---|
| Our World in Data | ourworldindata.org/food-choice-vs-eating-local | CC BY 4.0 | Per-kg CO₂ values for food categories |
| DEFRA | UK Government emission factors | Open Government License | Cross-reference for common items |
| Open Food Facts | world.openfoodfacts.org | Open Database License | Environmental scores for packaged goods |

## Appendix B: Key Reference Projects

| Project | URL | What We Took |
|---|---|---|
| KenMwaura1/Fast-Api-Grafana-Starter | github.com/KenMwaura1/Fast-Api-Grafana-Starter | Docker Compose + Grafana provisioning pattern |
| sgasser/receipt-ocr | github.com/sgasser/receipt-ocr | Gemini Vision receipt OCR minimal pattern |
| danieleforte92/PantryOps | github.com/danieleforte92/PantryOps | FEFO (First Expired First Out) logic |
| maks-p/restaurant_sales_forecasting | github.com/maks-p/restaurant_sales_forecasting | Day-of-week features for demand forecasting |
| samijullien/airlab-retail | github.com/samijullien/airlab-retail | Waste quantification methodology |

## Appendix C: Gemini API Quick Reference

```python
# Installation
pip install google-genai

# Basic structured output call
from google import genai
from google.genai import types

client = genai.Client(api_key="YOUR_KEY")

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=[
        types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),  # or audio/wav
        types.Part.from_text("Extract inventory items from this input"),
    ],
    config={
        "response_mime_type": "application/json",
        "response_json_schema": YourPydanticModel.model_json_schema(),
    },
)

result = YourPydanticModel.model_validate_json(response.text)
```

**Supported input types:**
- Text: Plain string
- Images: JPEG, PNG, WebP, GIF, BMP
- Audio: WAV, MP3, AIFF, AAC, OGG, FLAC
- Video: MP4, MPEG, MOV, AVI, FLV, MPG, WebM, WMV, 3GPP

**Audio specs:** 32 tokens/second, max 9.5 hours, auto-downsampled to 16Kbps

---

*Document Version: 3.1 | Updated: March 19, 2026 | Status: Implementation-Ready*

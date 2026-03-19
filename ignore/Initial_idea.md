🌍 Project Eco-Pulse V2.0: The Zero-Waste Inventory Engine

The Ultimate Blueprint & God-Document for the Green-Tech Hackathon

1. Executive Summary & Vision

The Problem: Small businesses (cafes) and non-profits lack the time for manual inventory entry and the analytics to prevent perishable waste. This leads to massive financial loss and a hidden, high carbon footprint. Existing tools are either dumb spreadsheets or bloated enterprise ERPs.
The Solution: A fully Dockerized, asynchronous, AI-powered inventory lifecycle manager.
The Magic: 1. Eco-Stream: Eliminates data entry via Multimodal AI (receipts/voice/images).
2. Waste-Zero Engine: Predicts run-out dates via deterministic math (Linear Regression) and rescues expiring goods via Generative AI (recipes/donations).
3. Fail-Safe Design: Built with strict fallbacks for when AI hallucinations occur or APIs fail, proving deep engineering maturity.

2. Core Architecture & Tech Stack (The Dockerized Monolith)

The entire project runs via a single docker-compose up -d command.

Backend API: Python (FastAPI). Chosen for native async support, BackgroundTasks (crucial for non-blocking AI calls), and easy linear regression via scikit-learn.

Data Validation: Pydantic. Enforces strict JSON schemas when extracting data from the LLM.

Database: PostgreSQL. Relational data for items, categories, and audit logs.

Analytics/Dashboard: Grafana + Prometheus. Zero-frontend-code, enterprise-grade dashboards.

AI Layer: Google Gemini 1.5 Flash API (Fast, Multimodal, and supports JSON Structured Outputs).

Testing: pytest + pytest-mock (Test-Driven Development approach).

3. The "Wow" Features & Fallback Engineering

Phase A: Frictionless Ingestion ("Eco-Stream")

The Feature: A multimodal endpoint (POST /ingest). Users upload a photo of a receipt, a pantry shelf, or send a natural language string ("Bought 50 organic apples, expires next Tuesday").

The Pipeline: 1. FastAPI receives the payload and passes it to the LLM via a Background Task (so the user gets a 202 Accepted instantly).
2. The LLM extracts data using a strict Pydantic schema: {item_name, quantity, unit, expiry_date, confidence_score}.
3. The backend matches the item against the synthetic "Green DB" to attach a Carbon Impact Score per unit.

CRITICAL FALLBACK (Hallucination/Low Confidence):

Trigger: If the LLM returns a confidence_score < 85% OR fails Pydantic validation.

Action: The data is diverted from the active_inventory table to a pending_human_review table. The dashboard flags this as "Requires Approval."

Phase B: Analytics & Forecasting ("Waste-Zero Engine")

The Feature: Real-time visibility and predictive burn-rates.

The Pipeline (Non-AI Math): A chron job uses simple Linear Regression on the last 14 days of usage data to calculate "Estimated Days of Supply Remaining". This shows judges you know when NOT to use expensive/slow AI.

The Dashboards (Grafana):

Triage Heatmap: Red (Expires < 2 days), Yellow (< 7 days), Green (Safe).

Burn-Down Chart: Historical usage vs. predicted run-out date.

Impact Tracker: "Kg of CO2 Saved by Utilizing Expiring Goods vs. Trashing."

Phase C: Circular Economy Routing (The Upgrade)

The Feature: Active triage for expiring items.

The Pipeline: When an item crosses the 3-day expiration threshold, the system triggers the Generative AI:

Cafe Mode: Generates a "Special of the Day" recipe to sell off expiring ingredients.

Community Mesh Mode (New Upgrade): Checks if any partner organizations in the DB need the item. If yes, it drafts a targeted email payload.

CRITICAL FALLBACK (API Failure/Timeout):

Trigger: LLM API rate-limits, drops connection, or times out (> 5 seconds).

Action: The system catches the TimeoutError and defaults to a hardcoded heuristic: It updates the DB item status to AUTO_DISCOUNT_50 and logs an AI_BYPASSED flag in the system audit trail.

4. Repository Structure & Deliverables Checklist

Your final GitHub repository should look exactly like this:

eco-pulse/
│
├── backend/
│   ├── main.py                 # FastAPI application
│   ├── ai_service.py           # Gemini API wrappers & prompts
│   ├── predictive_math.py      # Linear regression logic
│   ├── models.py               # SQLAlchemy & Pydantic models
│   ├── requirements.txt
│   └── Dockerfile
│
├── tests/
│   ├── test_ingestion_fallbacks.py
│   ├── test_timeout_heuristics.py
│   └── test_math_forecasting.py
│
├── data/                       # The "Synthetic Datasets"
│   ├── mock_inventory_events.csv
│   └── carbon_impact_db.csv
│
├── grafana/
│   └── provisioning/           # Auto-loads your dashboards on startup
│
├── docker-compose.yml
├── README.md                   # Includes Architecture & Tradeoffs
└── Demo_Video.mp4              # 5-7 minute screen recording


5. Synthetic Dataset Schemas (The "Green DB")

To make the Grafana dashboards look incredible, generate a CSV with ~500 rows of fake historical data.

carbon_impact_db.csv (Lookup Table)
| item_id | item_name | category | co2_per_unit_kg | preferred_partner_charity |
|---|---|---|---|---|
| 001 | Whole Milk | Dairy | 3.2 | FoodRescue Local |
| 002 | Printer Paper | Office | 1.1 | N/A |

mock_inventory_events.csv (Time-Series Data)
| event_id | timestamp | item_id | action_type | qty_change | notes |
|---|---|---|---|---|---|
| 1099 | 2024-10-24 08:00 | 001 | USE | -2 | Morning rush |
| 1100 | 2024-10-24 14:00 | 002 | ADD | +50 | Restock |

6. Test-Driven Development (TDD) Strategy

Judges will check your tests. Focus your tests strictly on the fallbacks and math, not just "does the API return 200".

# test_ingestion_fallbacks.py
from unittest.mock import patch
from backend.ai_service import process_receipt_image

def test_low_confidence_routes_to_pending_queue():
    # Arrange: Mock the LLM to return a 65% confidence score
    mock_llm_response = {"item": "Milk", "qty": 10, "confidence": 0.65}
    
    with patch('backend.ai_service.call_llm', return_value=mock_llm_response):
        # Act
        result = process_receipt_image("fake_image.jpg")
        
        # Assert
        assert result.status == "PENDING_HUMAN_REVIEW"
        assert result.saved_to_active_db == False

def test_llm_timeout_triggers_heuristic_discount():
    # Arrange: Mock a TimeoutError from the LLM
    with patch('backend.ai_service.call_llm', side_effect=TimeoutError):
        # Act
        result = process_expiring_triage(item_id="001")
        
        # Assert
        assert result.action_taken == "AUTO_DISCOUNT_50"
        assert result.ai_bypassed == True


7. Design Documentation: Architecture & Tradeoffs

(Copy-paste this exact section into your final README)

Architectural Tradeoffs:

Cloud LLM vs. Local Edge Model: * Tradeoff: We chose a cloud LLM (Gemini 1.5 Flash) over a local model (like Llama-3-8B). While a local model ensures strict data privacy (crucial for enterprise), the hardware constraints and inference latency during a local docker deployment are prohibitive.

Mitigation: We implemented a PII-scrubber layer that uses simple regex to remove phone numbers and credit card details from receipts before the image/text is sent to the cloud API.

FastAPI Background Tasks vs. Celery/Redis:

Tradeoff: We utilized FastAPI's built-in BackgroundTasks for asynchronous AI processing instead of deploying a full Celery/Redis message queue.

Reasoning: While Celery is more robust for enterprise scale, adding two additional containers (Redis/Celery worker) violates the "lightweight, easy-to-deploy" constraint for our target audience (small cafes/non-profits).

Predictive Math vs. Predictive AI: * Tradeoff: We used standard scikit-learn linear regression for burn-rate forecasting instead of an LLM.

Reasoning: LLMs are notoriously unreliable at arithmetic and time-series forecasting. Using deterministic math is orders of magnitude faster, computationally cheaper, and 100% accurate, reserving the AI exclusively for generative tasks (recipes/routing).

8. The 1-Week Execution Master-Plan

Day 1: Scaffolding & Data. Setup Docker Compose (FastAPI, Postgres, Grafana). Write a quick Python script to generate the mock_inventory_events.csv with realistic weekend spikes. Load it into Postgres.

Day 2: The TDD Foundation. Write the failing tests outlined in Section 6. Setup a simple GitHub Action to run pytest on push (Judges LOVE CI/CD).

Day 3: Ingestion Pipeline. Integrate the LLM API. Implement the strict Pydantic parsing. Build the Confidence Score routing logic. Make the ingestion tests pass.

Day 4: Triage & Forecasting. Implement the linear regression math. Implement the Generative "Save-It Strategy" prompt and the hardcoded TimeoutError fallback. Make the remaining tests pass.

Day 5: Grafana Magic. Connect Grafana directly to Postgres. Build the Heatmap, Burn-down charts, and the "Carbon Impact" panels using SQL queries. Export the dashboard JSON and put it in the grafana/provisioning folder so it auto-loads.

Day 6: Video Recording. Record the 5-7 minute demo (Script below).

Day 7: Polish & Submit. Ensure the README uses the template, lists all tests, and clearly explains tradeoffs. Submit the repo.

9. The 5-7 Minute Video Pitch Script (The Mic Drop)

Rule Check: Screen recording only. Audio required. Focus on technical behavior, not UI polish.

[0:00 - 1:00] The Hook & Problem:

Visual: Slide with the problem statement or just your README.

Audio: "Small businesses and community labs waste up to 15% of their inventory because manual tracking is tedious, and static spreadsheets don't warn you when assets are about to expire. Welcome to Eco-Pulse, a lightweight, AI-driven inventory engine."

[1:00 - 2:30] Ease of Entry (The Multimodal API):

Visual: Open Postman, Swagger UI, or your simple CLI. Upload a sample receipt image or type a messy natural language sentence. Show the Postgres DB instantly updating with strictly typed JSON data.

Audio: "We crush the 'Ease of Entry' metric by eliminating forms. Our asynchronous API parses messy inputs into structured data, calculating the carbon footprint instantly against our synthetic Green DB."

[2:30 - 4:00] The Analytics (Waste Reduction):

Visual: Switch to the Grafana Dashboard. Point out the dynamic charts.

Audio: "This is our Waste-Zero Engine. Notice the Burn-Rate forecast? We intentionally didn't use an LLM here. We used deterministic linear regression because it's more reliable for math. We save the AI for where it shines: generative triage."

[4:00 - 5:30] The Mic Drop (Testing the Edge Cases):

Visual: Show the code for your Generative Triage feature. THEN, intentionally break your internet connection or alter your API key to force a failure. Trigger the triage endpoint.

Audio: "We engineered this system for failure. Watch what happens when the LLM is unavailable or times out. The backend doesn't crash. It catches the error, degrades gracefully, applies a hardcoded 50% discount rule, and logs an audit trail that the AI was bypassed."

[5:30 - 7:00] Tests, Tradeoffs & Conclusion:

Visual: Open the terminal. Run pytest. Show the tests passing (specifically pointing to test_llm_timeout_triggers_heuristic_discount).

Audio: "We applied Test-Driven Development specifically for these fallbacks. Our main architectural tradeoff was using FastAPI Background Tasks instead of a heavy Redis queue to keep the deployment lightweight for our target audience. Thank you for watching."
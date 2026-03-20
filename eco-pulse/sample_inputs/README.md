# Sample Inputs — Attribution & Usage Guide

This directory contains sample files for demonstrating Eco-Pulse's multimodal
ingestion pipeline. These files are designed to test both **happy-path** and
**fallback** scenarios.

---

## 📄 Files

| File | Purpose | Expected AI Behaviour |
|---|---|---|
| `receipt_clear.txt` | Clear, well-formatted grocery receipt | High confidence (≥ 0.85) — items auto-ingested |
| `receipt_blurry.txt` | Noisy receipt with OCR-like artefacts | Low confidence (< 0.85) — triggers human review fallback |
| `voice_sample.txt` | Transcription simulating a voice memo | Used with `--text` flag to demo text ingestion |
| `grocery_list.csv` | CSV batch import file | Direct CSV ingestion — no AI needed |
| `camera_capture.jpg` | Photo of a grocery receipt | Image ingestion via Gemini vision — `--image` flag |
| `fridge_shelf.jpg` | Photo of a fridge shelf with items | Image ingestion — identifies items from shelf photo |
| `groceries.jpg` | Photo of grocery items / bags | Image ingestion — extracts items from a grocery haul photo |

---

## 🎯 Demo Scenarios

### Scenario 1: Clear Receipt (Happy Path)
```bash
eco-pulse ingest --text "$(cat sample_inputs/receipt_clear.txt)"
```
**Expected:** All items extracted with high confidence, auto-ingested to inventory.

### Scenario 2: Blurry Receipt (Fallback F1 — Low Confidence)
```bash
eco-pulse ingest --text "$(cat sample_inputs/receipt_blurry.txt)"
```
**Expected:** Some items flagged for human review due to low confidence.

### Scenario 3: Voice Memo Transcription
```bash
eco-pulse ingest --text "$(cat sample_inputs/voice_sample.txt)"
```
**Expected:** Natural language parsed by AI, items extracted and normalised.

### Scenario 4: CSV Batch Import
```bash
eco-pulse ingest --csv sample_inputs/grocery_list.csv
```
**Expected:** All items directly ingested without AI processing.

### Scenario 5: Camera Capture (Real Image)
```bash
eco-pulse ingest --image sample_inputs/camera_capture.jpg
```
**Expected:** Gemini vision extracts items from the receipt photo with high confidence.

### Scenario 6: Fridge Shelf Photo (Real Image)
```bash
eco-pulse ingest --image sample_inputs/fridge_shelf.jpg
```
**Expected:** Gemini vision identifies items visible on the fridge shelf.

### Scenario 7: Grocery Haul Photo (Real Image)
```bash
eco-pulse ingest --image sample_inputs/groceries.jpg
```
**Expected:** Gemini vision extracts items from the grocery haul photo.

---

## 🖼️ Image & Audio Notes

This directory includes **real image files** for demonstrating Gemini vision
ingestion alongside text-based alternatives:

- `camera_capture.jpg` — receipt photo for `--image` ingestion
- `fridge_shelf.jpg` — fridge shelf photo for `--image` ingestion
- `groceries.jpg` — grocery haul photo for `--image` ingestion

The `.txt` files serve as portable, git-friendly alternatives that exercise
the same AI extraction pipeline via the `--text` flag.

To test with audio:
1. Record a voice memo → `eco-pulse ingest --voice memo.wav`
2. Or use `--file` with a pre-recorded `.wav` for Docker/headless environments.

---

## 📜 Attribution

- **Receipt data**: Fictional grocery items with realistic pricing
- **Carbon impact values**: Adapted from [Our World in Data](https://ourworldindata.org/food-choice-vs-eating-local) per-kg food emissions
- **Shelf life data**: Based on USDA FoodKeeper App guidelines
- **Item categories**: Aligned with common grocery/institutional inventory systems

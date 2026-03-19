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
| `shelf_photo.txt` | Description simulating a pantry shelf photo | Mixed confidence — some items auto-ingested, others flagged |
| `voice_sample.txt` | Transcription simulating a voice memo | Used with `--text` flag to demo text ingestion |
| `grocery_list.csv` | CSV batch import file | Direct CSV ingestion — no AI needed |

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

### Scenario 3: Shelf Photo Description
```bash
eco-pulse ingest --text "$(cat sample_inputs/shelf_photo.txt)"
```
**Expected:** Mixed results — clear items auto-ingested, ambiguous items queued.

### Scenario 4: Voice Memo Transcription
```bash
eco-pulse ingest --text "$(cat sample_inputs/voice_sample.txt)"
```
**Expected:** Natural language parsed by AI, items extracted and normalised.

### Scenario 5: CSV Batch Import
```bash
eco-pulse ingest --csv sample_inputs/grocery_list.csv
```
**Expected:** All items directly ingested without AI processing.

---

## 🖼️ Image & Audio Notes

For a real demo, you would use actual image files (`.jpg`/`.png`) and audio
files (`.wav`) with the `--image` and `--voice` flags respectively. The text
files in this directory serve as portable, git-friendly alternatives that
exercise the same AI extraction pipeline via the `--text` flag.

To test with real images/audio:
1. Take a photo of a grocery receipt → `eco-pulse ingest --image photo.jpg`
2. Record a voice memo → `eco-pulse ingest --voice memo.wav`
3. The AI pipeline handles these identically to text, but via different
   input modalities (image → Gemini vision, audio → Gemini audio).

---

## 📜 Attribution

- **Receipt data**: Fictional grocery items with realistic pricing
- **Carbon impact values**: Adapted from [Our World in Data](https://ourworldindata.org/food-choice-vs-eating-local) per-kg food emissions
- **Shelf life data**: Based on USDA FoodKeeper App guidelines
- **Item categories**: Aligned with common grocery/institutional inventory systems

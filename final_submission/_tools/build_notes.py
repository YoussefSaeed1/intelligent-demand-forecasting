"""Regenerates 05_speaker_notes/SPEAKER_NOTES_AND_DEMO_SCRIPT.md from the speaker notes embedded in the deck.

Requires python-pptx.  Usage (repository root):  <python-with-python-pptx> final_submission/_tools/build_notes.py
"""

from pathlib import Path

from pptx import Presentation

ROOT = Path(__file__).resolve().parents[2]
deck = Presentation(ROOT / "final_submission/04_presentation/IDF_Viva_Presentation.pptx")
slides = list(deck.slides)
out = [
    "# Speaker notes and live demonstration script",
    "",
    f"Generated from the speaker notes embedded in `04_presentation/IDF_Viva_Presentation.pptx` ({len(slides)} slides: 23 for the talk, "
    "about "
    "20 minutes plus questions, and one appendix slide of production screenshots as the demo fallback). Every number is traceable to "
    "`02_traceability/EVIDENCE_TO_CLAIM_TRACEABILITY.md`.",
    "",
    "Timing guide: slides 1-3 (3 min), 4-6 data (3 min), 7-10 method (4 min), 11-13 results (3 min), 14-17 inventory and limits (4 min), "
    "18-20 application and demo (5 min including the live demo), 21-23 close (2 min). Slide 24 is a backup slide.",
    "",
]
for i, s in enumerate(slides, 1):
    title = s.shapes.title.text_frame.text if s.shapes.title is not None else ""
    notes = s.notes_slide.notes_text_frame.text.strip() if s.has_notes_slide else ""
    out += [f"## Slide {i}: {title}", "", notes, ""]
out += [
    "## Live demonstration script (detailed)",
    "",
    "Preparation (10 minutes before): open https://idf-web.vercel.app once so the Supabase Free project is awake; confirm `/api/v1/health` "
    "shows `status ok` and `engine.reachable true`; keep the Power BI report and appendix slide 24 ready as fallbacks.",
    "",
    "1. **Executive Overview** (30 s). Point to the three evidence labels: *Validated* (validation origins), *Reported* "
    "(sealed final holdout, "
    "never recomputed) and *Hypothetical* (inventory costs in NCU). Read the two headline cards: Store Item LightGBM validation MAE 6.308; "
    "M5 random forest 1.0201.",
    "2. **Forecast Explorer** (60 s). Store Item, series `store_item|1:11`, origin 1. Show the 84-day history, the 28 actual days and the "
    "three model forecasts; note the per-series MAE for each model and that the window ends before the final holdout.",
    "3. **Inventory Planner** (60 s). Click through with the same series and origin. Run the base scenario. Show the four totals and the "
    "*Saved Phase 5* column: they are equal (2,555 / 2,772 / 2,900 / 1,309 NCU for Selected ML, MA28, seasonal naive and fixed ROP). "
    "The live result comes from the protected engine, which loads the saved sales itself.",
    "4. **Custom scenario** (45 s). Set lead time 3 days and unmet-demand penalty 25 NCU; run. The page labels it a custom hypothetical "
    "scenario with no published reference. Export the CSV to show the NCU caveat line.",
    "5. **Scenario Comparison** (30 s). Store Item, origin filter 4: show that Selected ML is costlier than MA28 at origin 4 "
    "although it is "
    "more accurate.",
    "6. **Research and Methodology** (15 s). Show the protocol, the audit findings and the limitations list; the final holdout "
    "is presented "
    "as reported values only.",
    "",
    "Scope to state if asked: the application exposes curated series only (all 500 Store Item and 300 of 30,490 M5 series). "
    "Fallbacks: if the engine is unavailable the planner shows a labelled fallback to the saved Phase 5 results (designed behaviour). "
    "If the network fails, use appendix slide 24 and the Power BI report.",
    "",
    "## Anticipated examiner questions",
    "",
    "| Question | Short answer | Evidence |",
    "|---|---|---|",
    "| Why are the M5 models price-free? | Price publication latency relative to the forecast origin could not be verified, "
    "so using prices "
    "risked leakage. Phase 3 price-enabled runs are conditional references only. | PHASE4_FEATURE_AVAILABILITY.md |",
    "| Is the 57.6% Store Item improvement significant? | No significance claim; one final window. The direction was the same at all four "
    "validation origins. | Paper Tables 6 and 8 |",
    "| Why is fixed ROP the cheapest? | It holds about half the stock and serves less; on Store Item it degenerates into daily one-day "
    "replenishment. | Audit F-03; paper Table 11 |",
    "| Why does a more accurate forecast cost more? | Order-up-to policies react to the forecast level; a higher-level but more accurate "
    "forecast builds more stock. | Paper Section 9.2 |",
    "| Could the holdout have influenced selection? | The selection was fingerprinted before the read, forecasts were sealed, and each "
    "holdout was read once (12-event ledger). Limitation: timestamps are self-recorded. | Audit F-08 |",
    "| Who audited the work? | An AI-assisted review in a separate context (2026-11-10) and a Phase 8 second-pass review; neither is an "
    "external human examination. | 01_audits/ |",
    "| Why not add a better model now? | The holdout is consumed; any new model could only be compared on reused validation windows. | "
    "Audit section 9 |",
    "| What does NCU mean? | Normalised hypothetical cost units from frozen assumptions; not currency and never savings. | "
    "PHASE5_ASSUMPTIONS.md |",
    "| May the app display Kaggle sales? | Raw files are not redistributed; the demonstrator shows curated daily sales. The owner's review "
    "of the competitions' data-use terms is pending (open checklist item). | DATASETS.md; checklist |",
]
target = ROOT / "final_submission/05_speaker_notes/SPEAKER_NOTES_AND_DEMO_SCRIPT.md"
target.write_text("\n".join(out) + "\n", encoding="utf-8")
print("wrote", target, "slides", len(slides))

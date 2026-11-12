# Second-pass review of the Phase 8 deliverables

Date: 2026-11-13. Two reviews ran in **separate AI contexts** that had not written the deliverables. Both worked
read-only, and neither opened the sealed holdout. They are independent of the authoring context but are **not
external human examination**; validation by the supervisor or examiners remains outstanding.

| Review | Scope | Completed | Verdict |
|---|---|---|---|
| A. Evidence review | Numbers, methodology, inventory interpretation, citations, paper-deck-portfolio consistency, reproducibility claims, data-use terms | Yes. The first attempt on 2026-11-12 stopped on a usage limit; it was resumed and completed on 2026-11-13 | Numbers almost entirely correct; 0 Critical, 1 High, 5 Medium, 14 Low, 3 Informational |
| B. Visual and document QA | Every rendered page (Word 16) and slide (PowerPoint 16): overflow, overlap, tables, figures, captions, TOC, notes | Yes | No blocking defect; 2 High, 3 Medium, 9 Low, 3 Informational |

Reviewer A recomputed all 40 final-holdout metric values, the derived percentages, the per-series wins, every
inventory table value, all EDA statistics and the Phase 4 counts, and found them correct. It also confirmed that every
in-text citation has a reference entry, and the reverse.

## Disposition of findings

Statuses:

- **Fixed:** corrected and re-rendered.
- **Fixed (owner):** needs the owner.
- **Not a defect:** checked and rejected, with the reason given.
- **Accepted:** left as is, with the reason given.

| ID | Sev. | Finding | Disposition |
|---|---|---|---|
| A R-01 | High | The deliverables said the data were "used under their competition rules" and "not redistributed", while the public app displays daily sales of curated series and the data-use terms review is still open | **Partly fixed.** The wording in the paper, slide 4 and the portfolio now says the raw files are not redistributed, the demonstrator shows curated daily sales, and the owner's review of the terms is pending. **Blocker for the owner:** record the review of both competitions' rules. If they do not permit public display, restrict the app's display of actual sales (a production change that needs separate approval) |
| A R-02 | Medium | Paper Appendix E reported F-02 as "addressed" | Fixed: "Open: off-device copy pending owner action" |
| A R-03 | Medium | README and checklist referenced files that did not exist | Partly not a defect: `REMAINING_RISKS_AND_FOLLOW_UP.md` existed. Fixed by creating this review and the backup report after the backup ran |
| A R-04 | Medium | Phase 3 M5 RF and LightGBM were shown as plain results, but those runs were price-enabled | Fixed: Table 5 rows labelled "price-enabled, conditional"; the text cites the price-free anchors (RF 1.0267, LightGBM 1.0731); the ranking is unchanged |
| A R-05 | Medium | The portfolio showed only the MA28 cost comparison | Fixed: seasonal-naive row added (Store Item −1.10%, costlier at origin 3; M5 cheaper at all origins) |
| A R-06 | Medium | App coverage not stated where "serves exactly the recorded evidence" | Fixed: "for its curated series (all 500 Store Item and 300 of 30,490 M5 series)" in the paper, slide 21 and the portfolio |
| A R-07 | Low | "(51.34%)" placed next to MA28 | Fixed |
| A R-08 | Low | "All methods … full populations" while ARIMA/SARIMA ran on subsets | Fixed in the abstract, Section 8.1 ("53 Store Item and 51 M5 series"), slide 10 and the portfolio |
| A R-09 | Low | Replay provenance overstated | Fixed: the project's own 3,264 replays are distinguished from the independent audit's deterministic-policy re-simulation |
| A R-10 | Low | Sensitivity claim too general | Fixed: restricted to Store Item; the M5 sign depends on the scenario |
| A R-11 | Low | "worth its complexity" overstated | Fixed: "clearly more accurate on the one regular dataset studied, although its cost advantage was not robust" |
| A R-12 | Low | Power BI QA overstated | Fixed: "43-rule quality check (42 pass, 1 cosmetic warning)" |
| A R-13 | Low | Missing-price count attributed to the training prefix | Fixed: "full history" in Table 1; slide 6 gives 12,298,948 for the prefix |
| A R-14 | Low | "days" instead of series-day observations | Fixed on slide 2 and in the portfolio |
| A R-15 | Low | Slide 7 "Lags 1-56" | Fixed: "Lags 1, 7, 14, 28, 56" |
| A R-16 / B V-05 | Low / Medium | Inconsistent defect count | Fixed. There were two distinct defects: float rounding (fixed on two read paths) and a rejected TLS startup parameter. The paper, slide 20 and the notes now name both |
| A R-17 | Low | "never reaches the 11-day trigger" ambiguous | Fixed: "never rises above the 11-day reorder point" (paper and slide 16) |
| A R-18 | Low | Nature of the audit not disclosed | Fixed: described as an AI-assisted review in a separate context (paper Sections 1 and 12, slide 9, Q&A) |
| A R-19 | Low | COOP header claimed without evidence | Fixed with evidence: a live header check on 2026-11-13 returned `Cross-Origin-Opener-Policy: same-origin`, cited in the technical audit |
| A R-20 | Low | SBA bias attributed to the 2005 paper | Fixed: Syntetos and Boylan (2001) cited for the bias (Crossref-verified, IJPE 71, pp. 457–466); the 2005 paper for SBA's evaluation |
| A R-21 | Info | Conrad (1976) journal name | Fixed: *Operational Research Quarterly*, consistent with Croston (1972) |
| A R-22 | Info | Slide citations without a reference slide | Fixed: "Full references: research paper" on slides 5 and 10 |
| A R-23 / B V-01 | Info / High | Supervisor line blank | **Owner item** (the name is not in the repository) |
| B V-02 | High | The demo fallback referred to an appendix slide that did not exist | Fixed: appendix slide 24 with four production screenshots; the notes point to it |
| B V-03 | Medium | M5 bar axis not zero-based on slide 12 | Fixed: both final-holdout charts start at zero |
| B V-04 | Medium | Architecture diagram labels touching box borders | Fixed: re-laid-out figure (paper Figure 10, slide 18) |
| B V-06 | Low | Table split at a page foot | Fixed: rows cannot split; short tables are kept together |
| B V-07 | Low | White space on paper page 6 | Accepted (figure placement) |
| B V-08 | Low | "12-event" broken across lines | Fixed: non-breaking hyphen |
| B V-09 | Low | Slide 15 tick spacing | Fixed: 250 NCU major unit with 0 labelled |
| B V-10 | Low | "SN" undefined | Fixed: spelled out on slides 15 and 20 |
| B V-11 | Low | Footer and source lines too faint | Fixed: 10–11 pt, darker grey |
| B V-12 | Low | Planner screenshot unreadable | Fixed: cropped to the comparison table (live total vs saved Phase 5 total) on slide 19 and in paper Figure 11 |
| B V-13 | Low | Reference style | Partly not a defect: "et al." was already present. Fixed: the dataset note is now styled as a reference entry |
| B V-14 | Low | No space after the equations | Fixed |
| B V-15 | Info | Text-card slides 17, 21 and 22 | Accepted (limitations, contributions and closing) |
| B V-16 | Info | No declaration-of-originality page | **Owner item:** check the programme template |
| B V-17 | Info | Smallest figure text not judgeable at 70 dpi | Partly fixed: generated-figure footnotes raised to 10 pt. Reused Phase 2 EDA figures are unchanged (frozen evidence presentation) |

## Re-validation after the fixes

- Paper rebuilt; TOC updated in Word 16. 23 pages, 7,085 words, 16 tables, 11 figures, 22 references. Re-rendered and inspected.
- Deck rebuilt: 24 slides; schema validation passed; re-rendered in PowerPoint 16 and the changed slides inspected.
- Speaker notes regenerated from the deck (all 24 slides).
- Verification scripts re-run after lint tidying: identical results (validation MAE relative difference 0.0; Phase 5 discrepancy 0.0); figure data byte-identical.
- No change to any frozen scientific evidence, model, simulation, engine, database or deployment.

## Outstanding

1. Owner: record the Kaggle data-use terms review (R-01). If public display is not permitted, decide on restricting the app (separate approval).
2. Owner: supervisor name and any required declaration page (R-23, V-16).
3. External validation by the supervisor or examiners. These AI reviews do not substitute for it.

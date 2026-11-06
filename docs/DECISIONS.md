# Architecture and methodology decisions

All decisions dated 2026-11-06; revisit explicitly when evidence changes.

| ID | Decision and status | Rationale / consequence |
|---|---|---|
| ADR-001 | Accepted: src layout, setuptools, pyproject.toml | Installable single package; no services or database |
| ADR-002 | Accepted: YAML plus validated pathlib configuration | Central settings, dataset-free startup; no hidden env overrides |
| ADR-003 | Accepted: separate source adapters and namespaced daily schema | Datasets are independent; schema provisional until verified |
| ADR-004 | Accepted: chronological holdout and rolling validation | Protect future information; test never used for tuning |
| ADR-005 | Proposed: 28-day daily multi-step horizon | Comparable practical task; confirm coverage in Phase 1 |
| ADR-006 | Accepted: sales target and assumed inventory scenarios | Stock/cost inputs unverified; no actual savings claims |
| ADR-007 | Accepted: optional boosting/tuning/explain/tracking extras | Academic core first; avoid heavyweight initial installation |
| ADR-008 | Accepted: raw/generated data excluded from Git | Reproducibility through permitted manifests and hashes |
| ADR-009 | Accepted: Python 3.11 preferred, allow 3.11–3.14 | Local 3.14 available; do not claim compatibility tested on 3.11 |
| ADR-010 | Accepted: independent cross-dataset protocol first | Transfer is conditional, raw scale-dependent errors incomparable |
| ADR-011 | Accepted: reserve only requested package boundaries | No placeholder model classes or simulated results |

Dependency ranges provide initial compatibility; record a freeze after successful setup.
Do not describe that environment snapshot as a universal cross-platform lockfile.

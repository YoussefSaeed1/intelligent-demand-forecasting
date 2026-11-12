# Phase 7D rollback and recovery plan

Principles:
- The local checkpoint (`7000c04`), the Phase 4–7C backups and the frozen evidence are never touched by any rollback.
- Git does not undo database changes.
- Never delete the unrelated `semester-planner` projects or any other existing project.

| Failure | Detection | Recovery |
|---|---|---|
| Migration fails part-way | `apply_migration` error | The committed SQL has no explicit `BEGIN`/`COMMIT`, and whether `apply_migration` wraps it in a transaction is NOT VERIFIED, so assume partial objects may exist. In the new, dedicated project only, run `drop schema if exists app cascade; drop schema if exists ops cascade; drop role if exists webapp_api, engine_api, app_reader;`, fix the cause, then re-apply once. Never run this against any other project |
| Partial or incorrect data import | Seed count mismatch, D-L1 | The seed is one transaction (truncate, COPY, verify); on error it rolls back. Re-run the seed. Its hash check refuses CSVs that differ from the manifest |
| Scientific data mismatch | D-L1, D-L2, S-02 | Stop the public rollout; take the web project offline (pause or remove its domain). Re-verify the local CSVs against the manifest; never edit rows by hand |
| Wrong environment configuration | W-01 or E-01 failures, 503 `not_configured` | Correct the variable in the dashboard and redeploy; rotate any secret that may have been exposed (new value in both projects) |
| Leaked secret | Bundle or log scan, or accidental paste | Rotate immediately: `alter role … password` for the database roles; new `ENGINE_SHARED_KEY` in both projects; new salt. Redeploy both projects |
| Broken engine deployment | Build failure, E-checks | Use Instant Rollback to the previous production deployment if one exists; otherwise the web app degrades to the labelled precomputed fallback while the engine is fixed |
| Broken web deployment | W or S checks | Instant Rollback to the previous good deployment; with no previous one, remove the production domain until fixed |
| Rate-limit misconfiguration | W-04 or 429 floods | Adjust the `RATE_LIMIT_*` variables and redeploy; `ops.rate_limits` rows expire by window, and may be cleared by the owner (`delete from ops.rate_limits`) |
| Unexpected billing | Usage dashboards (O-01) | Hobby and Free pause rather than bill. If any paid prompt appears, decline it and stop; do not upgrade |
| Free project paused | Site errors after 7 idle days | Owner unpauses in the Supabase dashboard |

**Database backup:** Free-plan backups are limited. After a successful 7D-1, the owner may take a logical dump through the session
pooler (`pg_dump --schema=app --schema=ops`) into `C:/Project_Backups/` as a new folder. The authoritative restore path is
re-running the committed migration and the hash-verified seed from the local curated CSVs (deterministic; backed up).

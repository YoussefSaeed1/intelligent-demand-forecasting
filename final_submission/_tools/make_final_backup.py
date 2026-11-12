"""Phase 8 final backup: Git bundle + essential reproducibility and submission materials + SHA-256 manifest.

Usage (repository root):  .venv\\Scripts\\python.exe final_submission\\_tools\\make_final_backup.py <destination-folder>

Copies only the listed paths, never raw Kaggle data, environments, node_modules, build caches or .env files. After
copying, every file is re-read from the destination and re-hashed; the run fails if anything differs, or if a secret-like
pattern is found. Originals are never moved or modified. The destination must not exist (no overwrite).
"""

import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEST = Path(sys.argv[1])
INCLUDE = [
    "final_submission",
    "docs",
    "configs",
    "artifacts/experiments/phase4/frozen_selection.json",
    "artifacts/experiments/phase4/final_evaluation.json",
    "artifacts/experiments/phase4/final_metrics",
    "artifacts/experiments/phase4/holdout_access.jsonl",
    "artifacts/experiments/phase4/execution_contract.json",
    "artifacts/experiments/phase4/code_snapshot",
    "artifacts/inventory/phase5/plan.json",
    "artifacts/inventory/phase5/execution.json",
    "artifacts/webapp/data",
    "reports/inventory",
    "reports/data_quality",
    "reports/eda",
    "reports/forecasting/phase4_checkpoint_evidence",
    "reports/webapp/export_manifest.json",
    "reports/webapp/phase7d",
    "reports/powerbi",
    "powerbi",
]
EXCLUDE_PARTS = {"node_modules", ".venv", ".next", "__pycache__", ".pytest_cache", "cache", ".git"}
EXCLUDE_SUFFIX = {".pbix", ".pyc"}
EXCLUDE_NAMES = {".env", ".env.local", ".env.production", "localSettings.json", "cache.abf"}
SECRET = re.compile(
    rb"postgres(?:ql)?://[^\s\"'<>@:/]+:[^\s\"'<>@]{6,}@(?!127\.0\.0\.1|localhost)|-----BEGIN [A-Z ]*PRIVATE KEY|sk_live_|"
    rb"eyJ[A-Za-z0-9_-]{30,}\.[A-Za-z0-9_-]{20,}|x-vercel-protection-bypass\s*[:=]\s*[\"']?[A-Za-z0-9]{24,}"
)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 24), b""):
            h.update(block)
    return h.hexdigest()


def wanted(rel: Path):
    return not (set(rel.parts) & EXCLUDE_PARTS) and rel.suffix not in EXCLUDE_SUFFIX and rel.name not in EXCLUDE_NAMES


def main():
    if DEST.exists():
        raise SystemExit(f"Destination exists, refusing to overwrite: {DEST}")
    (DEST / "files").mkdir(parents=True)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    dirty = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    bundle = DEST / f"repository_main_{head[:7]}.bundle"
    subprocess.run(["git", "bundle", "create", str(bundle), "--all"], cwd=ROOT, check=True, capture_output=True)
    verify = subprocess.run(["git", "bundle", "verify", str(bundle)], cwd=ROOT, capture_output=True, text=True)
    if verify.returncode != 0:
        raise SystemExit("git bundle verify failed")
    entries, secrets = [], []
    for item in INCLUDE:
        src = ROOT / item
        if not src.exists():
            raise SystemExit(f"Missing required source: {item}")
        files = [src] if src.is_file() else sorted(p for p in src.rglob("*") if p.is_file())
        for f in files:
            rel = f.relative_to(ROOT)
            if not wanted(rel):
                continue
            out = DEST / "files" / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, out)
            entries.append({"path": rel.as_posix(), "bytes": f.stat().st_size, "sha256": sha256(f)})
            if f.suffix.lower() in {
                ".md",
                ".json",
                ".py",
                ".js",
                ".ts",
                ".tsx",
                ".yaml",
                ".yml",
                ".txt",
                ".csv",
                ".tmdl",
                ".toml",
                ".sql",
                ".ps1",
            }:
                if SECRET.search(f.read_bytes()):
                    secrets.append(rel.as_posix())
    entries.append({"path": bundle.name, "bytes": bundle.stat().st_size, "sha256": sha256(bundle), "kind": "git_bundle"})
    # Verify every copied file from the destination bytes.
    problems = []
    for e in entries:
        p = DEST / e["path"] if e.get("kind") == "git_bundle" else DEST / "files" / e["path"]
        if not p.exists() or sha256(p) != e["sha256"] or p.stat().st_size != e["bytes"]:
            problems.append(e["path"])
    sums = "".join(f"{e['sha256']}  {('' if e.get('kind') else 'files/')}{e['path']}\n" for e in entries)
    (DEST / "SHA256SUMS.txt").write_text(sums, encoding="utf-8")
    manifest = {
        "kind": "LOCAL BACKUP ON THE SAME DEVICE (Phase 8 essential package); not an off-device copy",
        "created_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "repository_head": head,
        "tracked_tree_clean": dirty == "",
        "git_bundle": bundle.name,
        "git_bundle_verify": verify.stdout.strip().splitlines()[-1] if verify.stdout.strip() else "ok",
        "file_count": len(entries),
        "total_bytes": sum(e["bytes"] for e in entries),
        "included_roots": INCLUDE,
        "excluded": "raw Kaggle data (data/raw, data/processed), virtual environments, node_modules, build caches, .env files, "
        "PBIX binaries, "
        "full Phase 4/5 model and prediction evidence (preserved in the verified Phase 4 and Phase 5 backups)",
        "verification": {"rehashed_from_destination": len(entries), "problems": problems, "secret_pattern_hits": secrets},
        "sha256sums_sha256": hashlib.sha256(sums.encode("utf-8")).hexdigest(),
        "files": entries,
    }
    (DEST / "BACKUP_MANIFEST.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                k: manifest[k]
                for k in ("repository_head", "tracked_tree_clean", "git_bundle_verify", "file_count", "total_bytes", "sha256sums_sha256")
            },
            indent=1,
        )
    )
    print("problems:", problems, "secret hits:", secrets)
    if problems or secrets:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

"""Re-hash every file of the existing local backups against their recorded manifests (read-only).

Usage: python verify_backups.py <output.json> [backup-root, default C:/Project_Backups]
"""

import hashlib
import json
import os
import sys

B = sys.argv[2] if len(sys.argv) > 2 else "C:/Project_Backups"  # optional: root of a copied backup set


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""):
            h.update(b)
    return h.hexdigest()


out = {}
for d in (
    "Demand_Forecasting_Phase4_Evidence_verified_20261108",
    "Demand_Forecasting_Phase5_Evidence_verified_20261108",
    "Demand_Forecasting_Phase6_PBIP_verified_20261110",
):
    v = json.load(open(f"{B}/{d}/BACKUP_VERIFICATION.json"))
    files = v["files"]
    bad = []
    n = 0
    size = 0
    for e in files:
        rel = e.get("path") or e.get("relative_path")
        exp = e.get("sha256")
        p = os.path.join(B, d, rel)
        if not os.path.exists(p):
            bad.append(("missing", rel))
            continue
        if sha(p) != exp:
            bad.append(("mismatch", rel))
        n += 1
        size += os.path.getsize(p)
    out[d] = {"files": len(files), "verified": n - len([b for b in bad if b[0] == "mismatch"]), "bytes": size, "problems": bad[:20]}
    print(d, out[d]["files"], "files;", "problems:", len(bad), flush=True)
d = "Demand_Forecasting_Phase7C_WebApp_verified_20261112"
bad = []
n = 0
for line in open(f"{B}/{d}/SHA256SUMS.txt", encoding="utf-8"):
    h, rel = line.rstrip("\n").split("  ", 1)
    n += 1
    p = os.path.join(B, d, rel)
    if not os.path.exists(p) or sha(p) != h:
        bad.append(rel)
out[d] = {"files": n, "problems": bad}
print(d, n, "files; problems:", len(bad))
json.dump(out, open(sys.argv[1], "w"), indent=1)

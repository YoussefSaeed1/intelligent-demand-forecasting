"""Local profiling run monitor; no network, credentials or source-file mutations."""

import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import psutil

directory = Path(__file__).resolve().parent
root = directory.parent.parent
started = datetime.now(UTC).isoformat()
clock = time.perf_counter()
peak_worker = 0
peak_tree_rss = 0
with (directory / "m5_verified.stdout.log").open("w", encoding="utf-8") as stdout:
    with (directory / "m5_verified.stderr.log").open("w", encoding="utf-8") as stderr:
        process = subprocess.Popen(
            [sys.executable, "-m", "intelligent_demand", "profile-data", "--dataset", "m5"],
            cwd=root,
            stdout=stdout,
            stderr=stderr,
        )
        parent = psutil.Process(process.pid)
        while process.poll() is None:
            try:
                members = [parent, *parent.children(recursive=True)]
            except psutil.Error:
                members = []
            rss = 0
            for member in members:
                try:
                    memory = member.memory_info()
                    rss += memory.rss
                    peak_worker = max(peak_worker, getattr(memory, "peak_wset", memory.rss))
                except psutil.Error:
                    pass
            peak_tree_rss = max(peak_tree_rss, rss)
            time.sleep(0.2)
        exit_code = process.wait()
metrics = {
    "started_at_utc": started,
    "finished_at_utc": datetime.now(UTC).isoformat(),
    "exit_code": exit_code,
    "elapsed_seconds": time.perf_counter() - clock,
    "peak_worker_working_set_bytes": peak_worker,
    "peak_process_tree_rss_bytes_sampled": peak_tree_rss,
    "measurement": "Windows process high-water working set; process tree RSS sampled every 0.2s",
}
(directory / "m5_verified_run.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
print(json.dumps(metrics, indent=2))
print((directory / "m5_verified.stderr.log").read_text(encoding="utf-8")[-6000:])
sys.exit(exit_code)

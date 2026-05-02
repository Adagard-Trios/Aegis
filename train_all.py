"""Trigger every pipeline's main.py with the root .env loaded.

Usage:

    python train_all.py                      # run all 12 pipelines
    python train_all.py --only fetal_health,parkinson_screener
    python train_all.py --skip ecg_arrhythmia,cardiac_age
    python train_all.py --large              # set MEDVERSE_FETCH_LARGE=true for this run

The script:

  1. Loads `.env` from the repo root via python-dotenv so KAGGLE_*,
     HF_TOKEN, SYNAPSE_AUTH_TOKEN, MEDVERSE_FETCH_LARGE etc. are visible
     to every pipeline subprocess.
  2. Iterates `models.registry.PIPELINES` (single source of truth).
  3. Runs `python main.py` inside each pipeline directory in its own
     subprocess so a crash in one doesn't kill the whole run.
  4. Streams stdout/stderr live (so you see the download progress bars)
     while still capturing the final result for the summary.
  5. Prints a per-pipeline status table at the end and writes the same
     to `train_all_results.json`.

Each pipeline's outcome is one of:
  - ok           → trained successfully, model.pkl on disk
  - gated        → DatasetUnavailable raised because a required env var is
                   missing (e.g., KAGGLE creds, MEDVERSE_FETCH_LARGE) — this
                   is correct behavior, not a bug
  - timeout      → exceeded the per-pipeline cap (configurable below)
  - fail         → unexpected error
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional

REPO = Path(__file__).resolve().parent
ENV_FILE = REPO / ".env"

# Per-pipeline timeout (seconds). Defaults are generous for downloads;
# override with --timeout when iterating.
PER_PIPELINE_TIMEOUT_S = {
    "bowel_motility":      120,
    "stress_ans":          120,
    "parkinson_screener":  300,
    "fetal_health":        300,
    "ecg_biometric":       1800,   # ~360 small PhysioNet files
    "preterm_labour":      1800,
    "lung_sound":          2400,   # ~600 MB ICBHI ZIP
    "ecg_arrhythmia":      90,     # gated by default → fail-fast
    "cardiac_age":         90,
    "skin_disease":        7200,   # ~1 GB Kaggle when creds present
    "retinal_disease":     7200,
    "retinal_age":         9000,   # + RETFound weights from HF
}


# ─── Helpers ────────────────────────────────────────────────────────────────


def load_dotenv() -> dict:
    """Read .env into the current process's os.environ. Returns a dict of
    only the new keys we set (not existing OS env)."""
    if not ENV_FILE.exists():
        print(f"[train_all] WARN: {ENV_FILE} not found — running with current env only")
        return {}
    set_keys: dict = {}
    try:
        from dotenv import dotenv_values
        for k, v in (dotenv_values(ENV_FILE) or {}).items():
            if v is None:
                continue
            os.environ[k] = v
            set_keys[k] = v
    except ImportError:
        # Lightweight fallback parser if python-dotenv isn't installed.
        for raw in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k:
                os.environ[k] = v
                set_keys[k] = v
    return set_keys


def load_pipelines() -> List[str]:
    """Return the canonical list of pipeline slugs from models/registry.py."""
    sys.path.insert(0, str(REPO))
    try:
        from models.registry import PIPELINES
        return [p.slug for p in PIPELINES]
    finally:
        if str(REPO) in sys.path:
            sys.path.remove(str(REPO))


def find_model_pkl(slug: str) -> Optional[str]:
    matches = sorted((REPO / "models" / slug).glob("artifacts/*/model_trainer/trained_model/model.pkl"))
    return str(matches[-1].relative_to(REPO)) if matches else None


def run_one(slug: str, *, clean: bool, timeout: int) -> dict:
    pipeline_dir = REPO / "models" / slug
    if not (pipeline_dir / "main.py").exists():
        return {"slug": slug, "status": "missing", "error_msg": f"{pipeline_dir}/main.py not found"}

    if clean:
        for sub in ("artifacts", "logs"):
            d = pipeline_dir / sub
            if d.exists():
                shutil.rmtree(d, ignore_errors=True)

    print(f"\n{'━' * 70}\n[{slug}]  cd {pipeline_dir.relative_to(REPO)} && python main.py\n{'━' * 70}", flush=True)

    t0 = time.time()
    try:
        proc = subprocess.Popen(
            [sys.executable, "main.py"],
            cwd=str(pipeline_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
    except Exception as e:
        return {"slug": slug, "status": "fail", "error_msg": f"failed to spawn: {e}"}

    captured: List[str] = []
    deadline = t0 + timeout
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            captured.append(line)
            print(line, end="", flush=True)
            if time.time() > deadline:
                proc.kill()
                proc.wait(timeout=5)
                return {
                    "slug": slug,
                    "status": "timeout",
                    "duration_s": round(time.time() - t0, 1),
                    "error_class": "Timeout",
                    "error_msg": f"exceeded {timeout}s",
                }
        proc.wait(timeout=5)
    except KeyboardInterrupt:
        proc.kill()
        raise

    duration = round(time.time() - t0, 1)
    full = "".join(captured)
    record: dict = {"slug": slug, "duration_s": duration}

    # Parse metrics where present
    m = re.search(r"f1_test=([0-9.]+)", full)
    if m:
        record["test_f1"] = float(m.group(1))
    m = re.search(r"r2_test=([-0-9.]+)\s+mae=([-0-9.]+)\s+rmse=([-0-9.]+)", full)
    if m:
        record["test_r2"] = float(m.group(1))
        record["mae"] = float(m.group(2))
        record["rmse"] = float(m.group(3))

    if proc.returncode == 0:
        record["status"] = "ok"
        record["model_pkl"] = find_model_pkl(slug)
    else:
        record["status"] = "fail"
        record["model_pkl"] = find_model_pkl(slug)
        # Surface the most-actionable error
        m = re.search(r"DatasetUnavailable: ([^\n]+)\s*\n→ ([^\n]+)", full)
        if m:
            record["error_class"] = "DatasetUnavailable"
            record["error_msg"] = m.group(1).strip()
            record["hint"] = m.group(2).strip()
            if any(t in record["error_msg"] + record["hint"]
                   for t in ("MEDVERSE_FETCH_LARGE", "KAGGLE", "HF_TOKEN", "SYNAPSE")):
                record["status"] = "gated"
        else:
            m = re.search(r"(NotImplementedError|ValueError|RuntimeError|FileNotFoundError|ImportError|ModuleNotFoundError):\s*([^\n]+)", full)
            if m:
                record["error_class"] = m.group(1)
                record["error_msg"] = m.group(2).strip()[:200]
            else:
                record["error_class"] = "Unknown"
                record["error_msg"] = (full.strip().splitlines()[-1] if full.strip() else "no output")[:200]
    return record


# ─── CLI ────────────────────────────────────────────────────────────────────


def main() -> int:
    p = argparse.ArgumentParser(description="Train every model pipeline from the root .env.")
    p.add_argument("--only", default="", help="comma-separated slugs to run (default: all)")
    p.add_argument("--skip", default="", help="comma-separated slugs to skip")
    p.add_argument("--no-clean", action="store_true", help="don't clear artifacts/ + logs/ before each run")
    p.add_argument("--timeout", type=int, default=0, help="override per-pipeline timeout (seconds)")
    p.add_argument("--large", action="store_true", help="set MEDVERSE_FETCH_LARGE=true for this run only")
    p.add_argument("--results", default="train_all_results.json", help="JSON results path")
    args = p.parse_args()

    set_keys = load_dotenv()
    if args.large:
        os.environ["MEDVERSE_FETCH_LARGE"] = "true"
        set_keys["MEDVERSE_FETCH_LARGE"] = "true"

    print(f"[train_all] loaded {len(set_keys)} vars from {ENV_FILE.name}")
    for k in ("KAGGLE_USERNAME", "HF_TOKEN", "SYNAPSE_AUTH_TOKEN", "MEDVERSE_FETCH_LARGE"):
        v = os.environ.get(k, "")
        flag = "set" if v and v.lower() not in ("false", "") else "unset"
        print(f"           {k} = {flag}")

    all_slugs = load_pipelines()
    only = {s.strip() for s in args.only.split(",") if s.strip()}
    skip = {s.strip() for s in args.skip.split(",") if s.strip()}
    todo = [s for s in all_slugs if (not only or s in only) and s not in skip]
    print(f"[train_all] running {len(todo)} of {len(all_slugs)} pipelines: {todo}")

    out_path = REPO / args.results
    results: List[dict] = []
    for slug in todo:
        timeout = args.timeout or PER_PIPELINE_TIMEOUT_S.get(slug, 600)
        try:
            r = run_one(slug, clean=not args.no_clean, timeout=timeout)
        except KeyboardInterrupt:
            print("\n[train_all] interrupted by user")
            r = {"slug": slug, "status": "interrupted"}
            results.append(r)
            out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
            break
        except Exception as e:
            r = {"slug": slug, "status": "runner_error", "error_msg": repr(e)}
        results.append(r)
        # Persist incrementally so a crash mid-run doesn't lose everything.
        out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    # Summary table
    print("\n" + "=" * 70)
    print("Pipeline run summary")
    print("=" * 70)
    print(f"{'Pipeline':<22} {'Status':<8} {'Time':>8}  {'Result':<60}")
    for r in results:
        status = r.get("status", "?")
        dur = f"{r.get('duration_s', 0):.1f}s"
        if "test_f1" in r:
            note = f"f1_test={r['test_f1']:.3f}  ->  {r.get('model_pkl', '')}"
        elif "test_r2" in r:
            note = f"r2_test={r['test_r2']:.3f}  ->  {r.get('model_pkl', '')}"
        elif "error_msg" in r:
            note = f"{r.get('error_class','')}: {r.get('error_msg','')[:60]}"
        else:
            note = ""
        print(f"{r['slug']:<22} {status:<8} {dur:>8}  {note}")

    ok_count = sum(1 for r in results if r.get("status") == "ok")
    gated_count = sum(1 for r in results if r.get("status") == "gated")
    print("\n" + "-" * 70)
    print(f"Trained: {ok_count}/{len(results)}    Gated (expected): {gated_count}    Other: {len(results) - ok_count - gated_count}")
    print(f"Results saved to {out_path}")

    # Exit non-zero if anything was unexpectedly broken (gated is fine)
    bad = [r for r in results if r.get("status") not in ("ok", "gated", "interrupted")]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

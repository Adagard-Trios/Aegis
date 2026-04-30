"""
src/utils/ctg_dawes_redman.py

Dawes-Redman-style CTG (cardiotocography) analysis for the obstetrics agent.

Proper Dawes-Redman criteria require at least a 10-minute FHR trace, so
this module maintains its own ring buffer of 1 Hz FHR samples independent
of app.py's 800-sample (~20 s) telemetry deques. Each 10 Hz SSE tick
feeds the latest FHR estimate into `DawesRedmanAnalyzer.ingest()`; the
analyzer down-samples to 1 Hz, keeps 30 minutes of history, and reports
the Dawes-Redman criteria whenever ≥10 minutes have accumulated.

Scope note: this is a *screening* surrogate of the full Dawes-Redman /
Sonicaid algorithm (which is commercial and closed). It captures:
  • baseline FHR (trimmed mean of the last 10 min)
  • short-term variation (STV, ms; mean |Δ RR| between consecutive beats)
  • accelerations (≥15 bpm rises held ≥15 s)
  • decelerations (≥15 bpm drops held ≥15 s)
  • criteria_met: baseline in 110–160 bpm, STV ≥ 3 ms, ≥1 accel, no
    significant decels.

All functions are tolerant of short / empty buffers — returns zeros +
`criteria_met: False` rather than raising, so the 10 Hz SSE loop is
never blocked.
"""
from __future__ import annotations

import threading
import time
from collections import deque
from typing import Optional


# ─── 1 Hz ring buffer (30 minutes = 1800 samples) ──────────────────────────

class DawesRedmanAnalyzer:
    """
    Thread-safe FHR accumulator + Dawes-Redman surrogate analyzer.

    A single module-level instance is exposed via `get_analyzer()`; there
    is one stream of fetal data per backend, so a singleton is fine.
    """

    HISTORY_SECONDS = 1800        # 30 min @ 1 Hz
    MIN_ANALYSIS_SECONDS = 600    # Dawes-Redman needs ≥10 min

    def __init__(self) -> None:
        self._fhr: deque = deque(maxlen=self.HISTORY_SECONDS)
        self._last_second: int = 0
        self._lock = threading.Lock()

    # ── ingestion ──────────────────────────────────────────────────

    def ingest(self, fhr_bpm: Optional[float], now: Optional[float] = None) -> None:
        """
        Append at most one sample per second (down-sampling from 10 Hz
        SSE). Silently drops NaN/None/non-physiologic values.
        """
        if fhr_bpm is None:
            return
        try:
            fhr = float(fhr_bpm)
        except (TypeError, ValueError):
            return
        if fhr <= 0 or fhr > 250:  # drop garbage
            return
        t = int(now or time.time())
        with self._lock:
            if t != self._last_second:
                self._fhr.append(fhr)
                self._last_second = t

    # ── analysis ───────────────────────────────────────────────────

    def analyze(self) -> dict:
        with self._lock:
            series = list(self._fhr)

        n = len(series)
        ready = n >= self.MIN_ANALYSIS_SECONDS
        if n == 0:
            return self._empty(ready=False)

        baseline = self._baseline(series)
        stv_ms = self._stv(series)
        accels = self._count_excursions(series, baseline, direction="up")
        decels = self._count_excursions(series, baseline, direction="down")

        criteria_met = bool(
            ready
            and 110.0 <= baseline <= 160.0
            and stv_ms >= 3.0
            and accels >= 1
            and decels == 0
        )

        return {
            "samples": n,
            "analysis_ready": ready,
            "baseline_fhr": round(baseline, 1),
            "stv_ms": round(stv_ms, 2),
            "accelerations": accels,
            "decelerations": decels,
            "criteria_met": criteria_met,
        }

    # ── helpers ────────────────────────────────────────────────────

    @staticmethod
    def _empty(ready: bool) -> dict:
        return {
            "samples": 0,
            "analysis_ready": ready,
            "baseline_fhr": 0.0,
            "stv_ms": 0.0,
            "accelerations": 0,
            "decelerations": 0,
            "criteria_met": False,
        }

    @staticmethod
    def _baseline(series: list) -> float:
        """Trimmed mean (drop top + bottom 10%) for robustness to excursions."""
        sorted_s = sorted(series)
        k = max(1, len(sorted_s) // 10)
        trimmed = sorted_s[k:-k] if len(sorted_s) > 2 * k else sorted_s
        return sum(trimmed) / len(trimmed) if trimmed else 0.0

    @staticmethod
    def _stv(series: list) -> float:
        """
        Short-term variation in ms. Using Δ RR between adjacent beats as a
        close proxy: Δ RR ≈ |60000/fhr[i] − 60000/fhr[i-1]|.
        """
        if len(series) < 2:
            return 0.0
        diffs = []
        for a, b in zip(series[:-1], series[1:]):
            if a > 0 and b > 0:
                diffs.append(abs(60000.0 / b - 60000.0 / a))
        return (sum(diffs) / len(diffs)) if diffs else 0.0

    @staticmethod
    def _count_excursions(
        series: list,
        baseline: float,
        direction: str,
        threshold_bpm: float = 15.0,
        min_hold_sec: int = 15,
    ) -> int:
        """
        Count qualifying accelerations (direction="up") or decelerations
        ("down"). Requires `threshold_bpm` sustained ≥ min_hold_sec.
        """
        if not series or baseline <= 0:
            return 0
        sign = 1 if direction == "up" else -1
        count = 0
        run = 0
        for v in series:
            if sign * (v - baseline) >= threshold_bpm:
                run += 1
                if run == min_hold_sec:
                    count += 1
            else:
                run = 0
        return count


# ─── Module singleton ──────────────────────────────────────────────────────

_singleton: Optional[DawesRedmanAnalyzer] = None


def get_analyzer() -> DawesRedmanAnalyzer:
    global _singleton
    if _singleton is None:
        _singleton = DawesRedmanAnalyzer()
    return _singleton


def ingest_fhr(fhr_bpm: Optional[float]) -> None:
    """Feed the latest FHR estimate (bpm) into the analyzer."""
    get_analyzer().ingest(fhr_bpm)


def get_ctg_analysis() -> dict:
    """Return the latest Dawes-Redman surrogate assessment."""
    return get_analyzer().analyze()

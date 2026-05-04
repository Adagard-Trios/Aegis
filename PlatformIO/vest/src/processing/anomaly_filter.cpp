#include "anomaly_filter.h"

#if EDGE_ANOMALY_ENABLED

AnomalyFilter::AnomalyFilter()
    : _hr_high_ticks(0),
      _hr_low_ticks(0),
      _spo2_low_ticks(0),
      _fired(false),
      _reason("none") {}

void AnomalyFilter::update(int hr_bpm, int spo2_pct) {
    // HR — only count ticks when we have a valid reading. The R-peak
    // detector returns 0 during the warmup window or when no peaks
    // have been seen recently; we don't want either case to trip a
    // bradycardia alert.
    if (hr_bpm > 0) {
        if (hr_bpm > ANOMALY_HR_MAX_BPM) {
            _hr_high_ticks++;
            _hr_low_ticks = 0;
        } else if (hr_bpm < ANOMALY_HR_MIN_BPM) {
            _hr_low_ticks++;
            _hr_high_ticks = 0;
        } else {
            _hr_high_ticks = 0;
            _hr_low_ticks = 0;
        }
    }

    // SpO2 — same gating; 0 means "no PPG / unfit signal", not hypoxia.
    if (spo2_pct > 0) {
        if (spo2_pct < ANOMALY_SPO2_MIN_PCT) {
            _spo2_low_ticks++;
        } else {
            _spo2_low_ticks = 0;
        }
    }

    // Trip on whichever band has held for the longest run; SpO2 takes
    // priority because hypoxia is the more time-critical of the three.
    if (_spo2_low_ticks >= ANOMALY_PERSIST_TICKS) {
        _fired = true;
        _reason = "spo2_low";
    } else if (_hr_high_ticks >= ANOMALY_PERSIST_TICKS) {
        _fired = true;
        _reason = "hr_high";
    } else if (_hr_low_ticks >= ANOMALY_PERSIST_TICKS) {
        _fired = true;
        _reason = "hr_low";
    } else {
        _fired = false;
        _reason = "none";
    }
}

void AnomalyFilter::clear() {
    _hr_high_ticks = 0;
    _hr_low_ticks = 0;
    _spo2_low_ticks = 0;
    _fired = false;
    _reason = "none";
}

#endif

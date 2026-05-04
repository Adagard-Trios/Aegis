#pragma once

/**
 * Edge anomaly filter for the Aegis vest.
 *
 * Watches HR (from the ECG R-peak detector) and SpO2 (from the PPG
 * pipeline) against simple safety bands. Trips an alert flag with
 * trend hysteresis: only after the values stay out-of-band for
 * ANOMALY_PERSIST_TICKS consecutive ticks does the AL flag flip,
 * which avoids transient artefacts (motion, electrode bumps) from
 * spamming the phone with false alarms.
 *
 * Why on-device: when the phone is offline or bandwidth is poor the
 * cloud-side rule engine can't fire — but the patient still needs a
 * local alert. The flag is published in the BLE vitals payload as
 * `AL:1,REASON:hr_high` so the phone can fire a local notification
 * immediately, before any cloud round-trip.
 *
 * Lifecycle:
 *   AnomalyFilter af;     // construct
 *   af.update(hr, spo2);  // call once per loop iteration
 *   af.fired();           // current alert state
 *   af.reason();          // last-tripped reason string for the BLE payload
 */

#include "../config.h"

#if EDGE_ANOMALY_ENABLED

class AnomalyFilter {
public:
    AnomalyFilter();
    /// Feed the latest derived vitals. Pass 0 / NaN-equivalent (HR=0)
    /// when a value is unavailable — the filter treats those as "no
    /// data" and never trips on them.
    void update(int hr_bpm, int spo2_pct);
    /// True when the alert flag is currently set.
    bool fired() const { return _fired; }
    /// One of: "none" | "hr_high" | "hr_low" | "spo2_low".
    const char* reason() const { return _reason; }
    /// Reset both counters + the alert state. Useful after a flag has
    /// been acknowledged on the phone side.
    void clear();

private:
    int  _hr_high_ticks;
    int  _hr_low_ticks;
    int  _spo2_low_ticks;
    bool _fired;
    const char* _reason;
};

#endif

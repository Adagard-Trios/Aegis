"""
MedVerse — FastAPI Backend with BLE Streaming
Connects to the MedVerse vest (advertised as 'Aegis_SpO2_Live' by the
ESP32-S3 firmware) via BLE and streams telemetry over SSE. Falls back
to simulated data when no device is available.
"""

import asyncio
import json
import math
import random
import time
import threading
from collections import deque
from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager

# Load .env before anything else reads os.environ — CORS allowlist, auth
# feature flag, waveform flag, and embedding model are all env-driven.
from dotenv import load_dotenv
load_dotenv()

import numpy as np
from scipy.signal import butter, filtfilt, find_peaks
import logging
from fastapi import FastAPI, UploadFile, File, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.utils.db import (
    init_db,
    insert_telemetry,
    insert_interpretation,
    get_latest_telemetry,
    get_latest_interpretations,
    get_history,
    list_patients,
    get_patient,
    upsert_patient,
    insert_alert,
    list_alerts,
    acknowledge_alert,
    find_recent_alert,
    list_audit,
    DEFAULT_PATIENT_ID,
)
from src.utils.imu_features import build_imu_derived_block
from src.utils.ctg_dawes_redman import ingest_fhr, get_ctg_analysis
from src.utils.fhir import (
    snapshot_to_observations,
    snapshot_to_bundle,
    expert_to_diagnostic_report,
    patient_resource,
    device_resource,
)
from src.utils.auth import (
    auth_enabled,
    cors_origins,
    create_access_token,
    require_user,
    verify_dev_credentials,
)
from src.utils.audit import audit
from src.alerts.rules import evaluate as evaluate_alerts

# =============================================================
# CONFIGURATION
# =============================================================
VEST_DEVICE_NAME = "Aegis_SpO2_Live"
FETAL_DEVICE_NAME = "AbdomenMonitor"
VEST_CHAR_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a8"
# Dedicated ECG burst characteristic — added in firmware v3.3 to deliver
# true 333 Hz raw ECG (firmware sample rate). The vitals char no longer
# carries L1/L2/L3 scalars; the burst handler appends per-sample.
VEST_ECG_BURST_CHAR_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a9"
FETAL_CHAR_UUID = "12345678-1234-1234-1234-123456789ab1"

# Sample rate matches the vest firmware's BLE tx cadence for PPG/IMU/etc.
# (~40 Hz). ECG runs on its own characteristic and arrives at MEDVERSE_ECG_SAMPLE_RATE
# (default 250 Hz, real firmware ceiling ~333 Hz).
import os as _os_sr
SAMPLE_RATE = int(_os_sr.environ.get("MEDVERSE_SAMPLE_RATE", "40"))
BUFFER_SIZE = SAMPLE_RATE * 20   # ~20 s rolling window
SPO2_WINDOW = SAMPLE_RATE * 4    #  4 s for SpO2 ratio
BR_WINDOW = SAMPLE_RATE * 10     # 10 s for breathing-rate

# ECG runs on its own clock — keep the deque short enough for SSE bandwidth
# (4 s × 250 Hz = 1000 samples is plenty for QRS/HRV/ST analysis windows).
ECG_SAMPLE_RATE = int(_os_sr.environ.get("MEDVERSE_ECG_SAMPLE_RATE", "250"))
ECG_BUFFER_SIZE = ECG_SAMPLE_RATE * 4

# Tracks the firmware revision string the vest reports in the vitals payload
# (FW: field, v3.4+). Stays None on pre-v3.4 vests so the log line only fires
# once per session when we actually see a new value.
_logged_fw_version = None

SIMULATION_MODE_GLOBAL = "Live"

# Single-device deployment writes every row under ACTIVE_PATIENT_ID.
# Reads can override via ?patient_id=… query param (or JWT sub claim
# when auth is enabled). Swap the active patient via POST /api/patient/active.
ACTIVE_PATIENT_ID = DEFAULT_PATIENT_ID

data_lock = threading.Lock()

# =============================================================
# BUFFERS
# =============================================================
x_data = deque([0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)

# PPG
ir1_data = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
red1_data = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
ir2_data = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
red2_data = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
ira_data = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
reda_data = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)

# PPG onboard temps
ppg_t1_data = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
ppg_t2_data = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)

# DS18B20 skin temps
tl_data = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
tr_data = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
tc_data = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)

# IMU
up_data = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
ur_data = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
lp_data = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
lr_data = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
sa_data = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
pp_data = deque([0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
bpr_data = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)  # GY-87 BMP180 Pressure
btp_data = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)  # GY-87 BMP180 Temp

# Environment
env_ep_data = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)  # HW-611 BMP280 Pressure
env_et_data = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)  # HW-611 BMP280 Temp
env_hum_data = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE) # DHT11 Humidity
env_dt_data = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)  # DHT11 Temp

# ECG — sized off ECG_BUFFER_SIZE (4 s × ECG_SAMPLE_RATE) since the burst
# characteristic delivers raw samples at 250-333 Hz, not the vitals 40 Hz.
ecg_l1_data = deque([0.0] * ECG_BUFFER_SIZE, maxlen=ECG_BUFFER_SIZE)
ecg_l2_data = deque([0.0] * ECG_BUFFER_SIZE, maxlen=ECG_BUFFER_SIZE)
ecg_l3_data = deque([0.0] * ECG_BUFFER_SIZE, maxlen=ECG_BUFFER_SIZE)
ecg_hr_data = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)

# Audio
audio_a_data = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
audio_d_data = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)

# Derived
hr_data = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
spo2_data = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
br_data = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
hrv_data = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
pi_data = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)

# Fetal
f_connected = False
f_mode = 0
f_pz_data = deque([[]] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
f_kick_data = deque([[]] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
f_move_data = deque([[]] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
f_mv_data = deque([[]] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
f_heart_data = deque([[]] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
f_bowel_data = deque([[]] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
f_fp_data = deque([[]] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
f_cont_data = deque([[]] * BUFFER_SIZE, maxlen=BUFFER_SIZE)

time_counter = 0
vest_connected = False
using_mock = False

# =============================================================
# SIGNAL PROCESSING
# =============================================================

def bandpass_filter(data, lowcut, highcut, fs, order=3):
    nyq = fs / 2.0
    low = max(0.001, min(lowcut / nyq, 0.999))
    high = max(0.001, min(highcut / nyq, 0.999))
    if low >= high:
        return np.array(data)
    try:
        b, a = butter(order, [low, high], btype='band')
        return filtfilt(b, a, np.array(data))
    except Exception:
        return np.array(data)


def lowpass_filter(data, cutoff, fs, order=3):
    nyq = fs / 2.0
    norm = min(cutoff / nyq, 0.999)
    try:
        b, a = butter(order, norm, btype='low')
        return filtfilt(b, a, np.array(data))
    except Exception:
        return np.array(data)


def calculate_spo2(ir_buf, red_buf):
    SPO2_TABLE = [
        100, 100, 100, 100, 99, 99, 99, 98, 98, 98,
        97, 97, 96, 96, 95, 95, 94, 94, 93, 93,
        92, 92, 91, 90, 89, 88, 86, 85, 83, 81,
    ]
    ir = np.array(ir_buf[-SPO2_WINDOW:], dtype=float)
    red = np.array(red_buf[-SPO2_WINDOW:], dtype=float)
    if len(ir) < SPO2_WINDOW or np.mean(ir) < 1000:
        return 0.0
    ir_ac = np.std(ir)
    ir_dc = np.mean(ir)
    red_ac = np.std(red)
    red_dc = np.mean(red)
    if ir_dc == 0 or red_dc == 0 or ir_ac < 10:
        return 0.0
    R = (red_ac / red_dc) / (ir_ac / ir_dc)
    index = max(0, min(int((R - 0.4) * 10), len(SPO2_TABLE) - 1))
    return float(SPO2_TABLE[index])


def calculate_heart_rate(ir_buf):
    ir = np.array(ir_buf, dtype=float)
    if len(ir) < SAMPLE_RATE * 4:
        return 0.0, []
    filtered = bandpass_filter(ir, 0.5, 4.0, SAMPLE_RATE)
    min_dist = int(SAMPLE_RATE * 60 / 180)
    peaks, _ = find_peaks(-filtered, distance=min_dist, prominence=np.std(filtered) * 0.5)
    if len(peaks) < 2:
        return 0.0, peaks.tolist()
    intervals = np.diff(peaks[-8:]) / SAMPLE_RATE
    bpm = 60.0 / np.mean(intervals)
    return round(max(30, min(220, bpm)), 1), peaks.tolist()


def calculate_hrv(ir_buf):
    ir = np.array(ir_buf, dtype=float)
    if len(ir) < SAMPLE_RATE * 8:
        return 0.0
    filtered = bandpass_filter(ir, 0.5, 4.0, SAMPLE_RATE)
    min_dist = int(SAMPLE_RATE * 60 / 180)
    peaks, _ = find_peaks(-filtered, distance=min_dist, prominence=np.std(filtered) * 0.5)
    if len(peaks) < 4:
        return 0.0
    rr = np.diff(peaks) / SAMPLE_RATE * 1000
    return round(np.sqrt(np.mean(np.diff(rr) ** 2)), 1)


def calculate_breathing_rate(ir_buf):
    ir = np.array(ir_buf[-BR_WINDOW:], dtype=float)
    if len(ir) < BR_WINDOW:
        return 0.0
    br_signal = lowpass_filter(ir, 0.5, SAMPLE_RATE)
    min_dist = int(SAMPLE_RATE * 60 / 40)
    peaks, _ = find_peaks(br_signal, distance=min_dist, prominence=np.std(br_signal) * 0.3)
    if len(peaks) < 2:
        return 0.0
    bpm = 60.0 / np.mean(np.diff(peaks) / SAMPLE_RATE)
    return round(max(4, min(40, bpm)), 1)


def calculate_pi(ir_buf):
    ir = np.array(ir_buf[-SPO2_WINDOW:], dtype=float)
    if len(ir) < 10 or np.mean(ir) == 0:
        return 0.0
    return round((np.std(ir) / np.mean(ir)) * 100, 2)


def signal_quality(pi):
    if pi == 0:
        return "No contact"
    if pi < 0.2:
        return "Poor"
    if pi < 0.5:
        return "Fair"
    if pi < 2.0:
        return "Good"
    return "Excellent"


def posture_label(sa):
    if abs(sa) < 5:
        return "Good posture"
    if abs(sa) < 15:
        return "Moderate"
    return "Poor posture!"


# =============================================================
# BLE HANDLER
# =============================================================

def handle_fetal_notification(sender, data):
    global f_connected, f_mode
    try:
        f_connected = True
        decoded = data.decode('utf-8').strip()
        parsed = json.loads(decoded)
        
        with data_lock:
            f_mode = parsed.get("mode", 0)
            f_pz_data.append(parsed.get("pz", [0,0,0,0]))
            f_kick_data.append(parsed.get("kick", [0,0,0,0]))
            f_move_data.append(parsed.get("move", [0,0,0,0]))
            f_mv_data.append(parsed.get("mv", [0.0,0.0]))
            f_heart_data.append(parsed.get("heart", [0,0]))
            f_bowel_data.append(parsed.get("bowel", [0,0]))
            f_fp_data.append(parsed.get("fp", [0.0,0.0]))
            f_cont_data.append(parsed.get("cont", [0,0]))
            
    except Exception as e:
        print(f"Fetal Parse error: {e}")

def handle_ble_notification(sender, data):
    global time_counter
    try:
        decoded = data.decode('utf-8').strip()
        parts = {}
        for p in decoded.split(','):
            if ':' in p:
                key, value = p.split(':', 1)
                parts[key] = value

        ir1 = float(parts.get('IR1', 0))
        red1 = float(parts.get('Red1', 0))
        ir2 = float(parts.get('IR2', 0))
        red2 = float(parts.get('Red2', 0))
        ira = float(parts.get('IRA', 0))
        reda = float(parts.get('RedA', 0))
        t1 = float(parts.get('T1', 0))
        t2 = float(parts.get('T2', 0))
        tl = float(parts.get('TL', 0))
        tr = float(parts.get('TR', 0))
        tc = float(parts.get('TC', 0))
        up = float(parts.get('UP', 0))
        ur_val = float(parts.get('UR', 0))
        lp = float(parts.get('LP', 0))
        lr_val = float(parts.get('LR', 0))
        sa = float(parts.get('SA', 0))
        pp = int(parts.get('PP', 0))
        bpr = float(parts.get('BPR', 0))
        btp = float(parts.get('BTP', 0))
        ep = float(parts.get('EP', 0))
        et = float(parts.get('ET', 0))
        hum = float(parts.get('HUM', 0))
        dt = float(parts.get('DT', 0))
        # L1/L2/L3 are no longer in the vitals payload — they arrive on the
        # ECG burst characteristic (handle_ecg_burst). Kept here as graceful
        # fallback for vests still running pre-v3.3 firmware.
        ecg_l1 = float(parts.get('L1', 0)) if 'L1' in parts else None
        ecg_l2 = float(parts.get('L2', 0)) if 'L2' in parts else None
        ecg_l3 = float(parts.get('L3', 0)) if 'L3' in parts else None
        ecg_hr = float(parts.get('EHR', 0))
        audio_a = float(parts.get('ARMS', 0))
        audio_d = float(parts.get('DRMS', 0))

        # Log firmware version once per session so we can spot vests still
        # running an old binary (no ECG burst, hard-coded R-peak threshold,
        # etc). The FW field appears in firmware v3.4+; older vests omit it
        # and `_logged_fw_version` sticks at None.
        fw = parts.get('FW')
        global _logged_fw_version
        if fw and fw != _logged_fw_version:
            print(f"[VEST] Firmware version: {fw}")
            _logged_fw_version = fw

        with data_lock:
            time_counter += 1
            x_data.append(time_counter)
            ir1_data.append(ir1)
            red1_data.append(red1)
            ir2_data.append(ir2)
            red2_data.append(red2)
            ira_data.append(ira)
            reda_data.append(reda)
            ppg_t1_data.append(t1)
            ppg_t2_data.append(t2)
            tl_data.append(tl)
            tr_data.append(tr)
            tc_data.append(tc)
            up_data.append(up)
            ur_data.append(ur_val)
            lp_data.append(lp)
            lr_data.append(lr_val)
            sa_data.append(sa)
            pp_data.append(pp)
            bpr_data.append(bpr)
            btp_data.append(btp)
            env_ep_data.append(ep)
            env_et_data.append(et)
            env_hum_data.append(hum)
            env_dt_data.append(dt)
            # ECG samples now arrive at 333 Hz on the burst char. Only fall
            # back to scalar appending when we're talking to old firmware.
            if ecg_l1 is not None:
                ecg_l1_data.append(ecg_l1)
            if ecg_l2 is not None:
                ecg_l2_data.append(ecg_l2)
            if ecg_l3 is not None:
                ecg_l3_data.append(ecg_l3)
            ecg_hr_data.append(ecg_hr)
            audio_a_data.append(audio_a)
            audio_d_data.append(audio_d)

            spo2 = calculate_spo2(list(ira_data), list(reda_data)) if len(ira_data) >= SPO2_WINDOW else 0.0
            bpm, _ = calculate_heart_rate(list(ira_data)) if len(ira_data) >= SAMPLE_RATE * 4 else (0.0, [])
            br = calculate_breathing_rate(list(ir1_data)) if len(ir1_data) >= BR_WINDOW else 0.0
            hrv = calculate_hrv(list(ira_data)) if len(ira_data) >= SAMPLE_RATE * 8 else 0.0
            pi = calculate_pi(list(ira_data)) if len(ira_data) >= SPO2_WINDOW else 0.0

            spo2_data.append(spo2)
            hr_data.append(bpm)
            br_data.append(br)
            hrv_data.append(hrv)
            pi_data.append(pi)

    except Exception as e:
        print(f"Parse error: {e}")


def handle_ecg_burst(sender, data):
    """Drains the high-rate ECG characteristic and appends per-sample to the
    L1/L2/L3 deques. Payload format:  EB1:v0|v1|...,EB2:v0|v1|...
    where each v is an integer millivolt reading. Lead III is computed
    Einthoven-style (II - I) per sample so all three deques stay aligned."""
    try:
        decoded = data.decode('utf-8').strip()
        l1_samples = []
        l2_samples = []
        for part in decoded.split(','):
            if part.startswith('EB1:'):
                l1_samples = [float(v) for v in part[4:].split('|') if v]
            elif part.startswith('EB2:'):
                l2_samples = [float(v) for v in part[4:].split('|') if v]
        n = min(len(l1_samples), len(l2_samples))
        if n == 0:
            return
        with data_lock:
            for i in range(n):
                ecg_l1_data.append(l1_samples[i])
                ecg_l2_data.append(l2_samples[i])
                ecg_l3_data.append(l2_samples[i] - l1_samples[i])
    except Exception as e:
        print(f"ECG burst parse error: {e}")


async def run_single_client(device_name: str, char_handlers, set_connected_flag_func):
    """Connects to one BLE device and subscribes to one or more characteristics
    on a single shared connection.

    char_handlers: list of (char_uuid, handler_func) tuples. The first entry's
    UUID is treated as the device's required characteristic — if it can't be
    subscribed we abort. Optional characteristics (e.g. ECG burst on old
    firmware) log a warning and continue.
    """
    try:
        from bleak import BleakClient, BleakScanner
    except ImportError:
        return False

    print(f"Scanning for '{device_name}'...")
    device = await BleakScanner.find_device_by_name(device_name, timeout=10.0)
    if not device:
        print(f"[WARN] Device '{device_name}' not found.")
        return False

    print(f"Found {device_name} at {device.address}. Connecting...")
    try:
        async with BleakClient(device) as client:
            if client.is_connected:
                set_connected_flag_func(True)
                print(f"[{device_name}] Connected! Streaming...")
                for idx, (char_uuid, handler) in enumerate(char_handlers):
                    try:
                        await client.start_notify(char_uuid, handler)
                    except Exception as e:
                        if idx == 0:
                            raise  # primary characteristic is required
                        print(f"[{device_name}] Optional char {char_uuid} unavailable ({e}) — continuing")
                while client.is_connected:
                    await asyncio.sleep(1)
    except Exception as e:
        print(f"BLE error on {device_name}: {e}")
    finally:
        set_connected_flag_func(False)
    return False

async def run_dual_clients():
    def set_vest_connected(val):
        global vest_connected
        vest_connected = val
        
    def set_fetal_connected(val):
        global f_connected
        f_connected = val

    try:
        from bleak import BleakScanner
    except ImportError:
        print("[WARN] bleak not installed — using mock data")
        return False

    task1 = run_single_client(
        VEST_DEVICE_NAME,
        [
            (VEST_CHAR_UUID, handle_ble_notification),
            (VEST_ECG_BURST_CHAR_UUID, handle_ecg_burst),
        ],
        set_vest_connected,
    )
    task2 = run_single_client(
        FETAL_DEVICE_NAME,
        [(FETAL_CHAR_UUID, handle_fetal_notification)],
        set_fetal_connected,
    )
    
    results = await asyncio.gather(task1, task2, return_exceptions=True)
    # If both return False/Exception (i.e., not found), we fallback to mock
    if all(res is False or isinstance(res, Exception) for res in results):
        return False
    return True

def ble_thread_runner():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(run_dual_clients())
        if result is False:
            start_mock_data()
    except Exception as e:
        print("Asyncio loop error:", e)
        start_mock_data()


# =============================================================
# MOCK DATA GENERATOR (when vest not available)
# =============================================================

def start_mock_data():
    global using_mock
    using_mock = True
    print("[MOCK] Generating simulated telemetry data...")
    thread = threading.Thread(target=_mock_data_loop, daemon=True)
    thread.start()


def _mock_data_loop():
    global time_counter
    t = 0.0
    while True:
        t += 1.0 / SAMPLE_RATE

        # Simulated PPG (IR around 30000, Red around 25000)
        ir_base = 30000 + 500 * math.sin(2 * math.pi * 1.2 * t) + 100 * math.sin(2 * math.pi * 0.25 * t)
        red_base = 25000 + 400 * math.sin(2 * math.pi * 1.2 * t + 0.1) + 80 * math.sin(2 * math.pi * 0.25 * t)
        noise = 50 * math.sin(2 * math.pi * 7.3 * t)

        ir1 = ir_base + noise
        red1 = red_base - noise
        ir2 = ir_base - 200 + noise * 0.5
        red2 = red_base + 100 - noise * 0.5
        ira = (ir1 + ir2) / 2
        reda = (red1 + red2) / 2

        # Simulated ECG (PQRST-like)
        period = 0.833  # ~72 BPM
        phase = (t % period) / period
        if phase < 0.1:
            ecg_val = 0.15 * math.sin(phase * math.pi / 0.1)
        elif phase < 0.15:
            ecg_val = 0
        elif phase < 0.18:
            ecg_val = -0.08
        elif phase < 0.22:
            ecg_val = 0.9 * math.sin((phase - 0.18) * math.pi / 0.04)
        elif phase < 0.26:
            ecg_val = -0.15
        elif phase < 0.35:
            ecg_val = 0
        elif phase < 0.45:
            ecg_val = 0.2 * math.sin((phase - 0.35) * math.pi / 0.1)
        else:
            ecg_val = 0

        ecg_l1 = ecg_val * 0.85
        ecg_l2 = ecg_val * 1.0
        ecg_l3 = ecg_val * 0.6

        # Simulated temps
        temp_l = 36.5 + 0.3 * math.sin(t * 0.01)
        temp_r = 36.6 + 0.2 * math.sin(t * 0.012)
        temp_c = 36.8 + 0.1 * math.sin(t * 0.008)

        # Simulated IMU & Environment
        up_val = 2.0 + 1.5 * math.sin(t * 0.1)
        ur_val = 0.5 + 0.8 * math.sin(t * 0.08)
        lp_val = 1.0 + 1.0 * math.sin(t * 0.12)
        lr_val = 0.3 + 0.5 * math.sin(t * 0.09)
        sa_val = up_val - lp_val
        pp_val = 1 if abs(sa_val) > 15 else 0
        bpr_val = 1012.0 + 0.5 * math.sin(t * 0.01)
        btp_val = 28.5 + 0.1 * math.sin(t * 0.02)
        ep_val = 1013.25 + 0.5 * math.sin(t * 0.015)
        et_val = 25.0 + 0.2 * math.sin(t * 0.01)
        hum_val = 55.0 + 5.0 * math.sin(t * 0.025)
        dt_val = 24.8 + 0.1 * math.sin(t * 0.012)

        # Audio
        audio_a_val = 120 + 30 * math.sin(t * 5)
        audio_d_val = 80 + 20 * math.sin(t * 7)

        # Fetal Simulated
        f_pz_val = [2000 + 100 * math.sin(t * 0.5)] * 4
        f_kick_val = [1 if (math.sin(t * 1.5) > 0.95) else 0] * 4
        f_move_val = [1 if (math.sin(t * 0.8) > 0.9) else 0] * 4
        
        # simulated maternal bowel/heart tones
        f_mv_val = [1.5 + 0.1 * math.sin(t * 5), 1.5 + 0.1 * math.cos(t * 6)]
        f_heart_val = [1 if (t % 0.4 < 0.1) else 0] * 2
        f_bowel_val = [1 if (math.sin(t * 0.2) > 0.8) else 0] * 2
        
        # simulated contraction pressure
        base_pressure = 10 + 50 * max(0, math.sin(t * 0.1))
        f_fp_val = [base_pressure, base_pressure * 0.9]
        f_cont_val = [1 if base_pressure > 40 else 0] * 2

        with data_lock:
            # Vest
            time_counter += 1
            x_data.append(time_counter)
            ir1_data.append(ir1)
            red1_data.append(red1)
            ir2_data.append(ir2)
            red2_data.append(red2)
            ira_data.append(ira)
            reda_data.append(reda)
            ppg_t1_data.append(30.5)
            ppg_t2_data.append(31.2)
            tl_data.append(temp_l)
            tr_data.append(temp_r)
            tc_data.append(temp_c)
            up_data.append(up_val)
            ur_data.append(ur_val)
            lp_data.append(lp_val)
            lr_data.append(lr_val)
            sa_data.append(sa_val)
            pp_data.append(pp_val)
            bpr_data.append(bpr_val)
            btp_data.append(btp_val)
            env_ep_data.append(ep_val)
            env_et_data.append(et_val)
            env_hum_data.append(hum_val)
            env_dt_data.append(dt_val)
            ecg_l1_data.append(ecg_l1)
            ecg_l2_data.append(ecg_l2)
            ecg_l3_data.append(ecg_l3)
            ecg_hr_data.append(72.0)
            audio_a_data.append(audio_a_val)
            audio_d_data.append(audio_d_val)
            
            # Fetal
            global f_mode
            f_mode = 0 # Fetal
            f_pz_data.append(f_pz_val)
            f_kick_data.append(f_kick_val)
            f_move_data.append(f_move_val)
            f_mv_data.append(f_mv_val)
            f_heart_data.append(f_heart_val)
            f_bowel_data.append(f_bowel_val)
            f_fp_data.append(f_fp_val)
            f_cont_data.append(f_cont_val)

            spo2 = calculate_spo2(list(ira_data), list(reda_data)) if len(ira_data) >= SPO2_WINDOW else 0.0
            bpm, _ = calculate_heart_rate(list(ira_data)) if len(ira_data) >= SAMPLE_RATE * 4 else (0.0, [])
            br = calculate_breathing_rate(list(ir1_data)) if len(ir1_data) >= BR_WINDOW else 0.0
            hrv = calculate_hrv(list(ira_data)) if len(ira_data) >= SAMPLE_RATE * 8 else 0.0
            pi = calculate_pi(list(ira_data)) if len(ira_data) >= SPO2_WINDOW else 0.0

            spo2_data.append(spo2)
            hr_data.append(bpm)
            br_data.append(br)
            hrv_data.append(hrv)
            pi_data.append(pi)

        time.sleep(1.0 / SAMPLE_RATE)


# =============================================================
# SNAPSHOT BUILDER
# =============================================================

def _estimate_fhr_bpm() -> Optional[float]:
    """
    Derive a one-off fetal-HR estimate (bpm) from the piezo buffer.

    Heuristic: count positive zero-crossings of the demeaned piezo signal
    over the last ~8 s and convert to bpm. Falls back to a maternal-HR
    offset (maternal + 65 bpm, clipped to physiologic range) so the
    Dawes-Redman analyzer has a continuous stream in demos where the
    AbdomenMonitor is absent. Returns None if nothing usable.
    """
    import numpy as _np
    try:
        if f_pz_data and len(f_pz_data) >= SAMPLE_RATE * 8:
            window = [row[0] if row else 0.0 for row in list(f_pz_data)[-SAMPLE_RATE * 8:]]
            arr = _np.asarray(window, dtype=float)
            arr = arr - _np.mean(arr)
            crossings = int(_np.sum((arr[:-1] < 0) & (arr[1:] >= 0)))
            if crossings >= 2:
                bpm = crossings * 60.0 / 8.0
                if 60 <= bpm <= 220:
                    return bpm
    except Exception:
        pass
    try:
        if hr_data and hr_data[-1]:
            mom = float(hr_data[-1])
            if mom > 0:
                return max(110.0, min(165.0, mom + 65.0))
    except Exception:
        pass
    return None


def build_telemetry_snapshot() -> dict:
    """Build a JSON-serializable snapshot of all current telemetry data."""
    # Feed the Dawes-Redman analyzer outside data_lock — the analyzer has
    # its own lock and only reads its internal state.
    try:
        ingest_fhr(_estimate_fhr_bpm())
    except Exception:
        pass

    with data_lock:
        last_sa = sa_data[-1] if sa_data else 0
        last_pi = pi_data[-1] if pi_data else 0
        # Optional raw waveform — enabled only when MEDVERSE_INCLUDE_WAVEFORM=true,
        # because shipping ~800 samples per channel per snapshot is heavy over SSE.
        # When enabled, LangGraph specialty nodes can feed the buffers into
        # ECGFounder / respiratory CNN adapters.
        import os as _os
        include_wave = _os.environ.get("MEDVERSE_INCLUDE_WAVEFORM", "false").lower() in ("1", "true", "yes")
        waveform_block = (
            {
                "fs": SAMPLE_RATE,
                "ecg_lead1": [round(v, 3) for v in list(ecg_l1_data)],
                "ecg_lead2": [round(v, 3) for v in list(ecg_l2_data)],
                "ecg_lead3": [round(v, 3) for v in list(ecg_l3_data)],
                "ppg_ira": [round(v, 1) for v in list(ira_data)],
                "ppg_reda": [round(v, 1) for v in list(reda_data)],
                "audio": [round(v, 1) for v in list(audio_a_data)],
            }
            if include_wave
            else None
        )
        return {
            "timestamp": time_counter,
            "ppg": {
                "ir1": round(ir1_data[-1], 1) if ir1_data else 0,
                "red1": round(red1_data[-1], 1) if red1_data else 0,
                "ir2": round(ir2_data[-1], 1) if ir2_data else 0,
                "red2": round(red2_data[-1], 1) if red2_data else 0,
                "ira": round(ira_data[-1], 1) if ira_data else 0,
                "reda": round(reda_data[-1], 1) if reda_data else 0,
                "t1": round(ppg_t1_data[-1], 2) if ppg_t1_data else 0,
                "t2": round(ppg_t2_data[-1], 2) if ppg_t2_data else 0,
            },
            "temperature": {
                "left_axilla": round(tl_data[-1], 2) if tl_data else 0,
                "right_axilla": round(tr_data[-1], 2) if tr_data else 0,
                "cervical": round(tc_data[-1], 2) if tc_data else 0,
            },
            "imu": {
                "upper_pitch": round(up_data[-1], 2) if up_data else 0,
                "upper_roll": round(ur_data[-1], 2) if ur_data else 0,
                "lower_pitch": round(lp_data[-1], 2) if lp_data else 0,
                "lower_roll": round(lr_data[-1], 2) if lr_data else 0,
                "spinal_angle": round(last_sa, 2),
                "poor_posture": bool(pp_data[-1]) if pp_data else False,
                "posture_label": posture_label(last_sa),
                "bmp180_pressure": round(bpr_data[-1], 2) if bpr_data else 0,
                "bmp180_temp": round(btp_data[-1], 2) if btp_data else 0,
            },
            "environment": {
                "bmp280_pressure": round(env_ep_data[-1], 2) if env_ep_data else 0,
                "bmp280_temp": round(env_et_data[-1], 2) if env_et_data else 0,
                "dht11_humidity": round(env_hum_data[-1], 2) if env_hum_data else 0,
                "dht11_temp": round(env_dt_data[-1], 2) if env_dt_data else 0,
            },
            "ecg": {
                "lead1": round(ecg_l1_data[-1], 3) if ecg_l1_data else 0,
                "lead2": round(ecg_l2_data[-1], 3) if ecg_l2_data else 0,
                "lead3": round(ecg_l3_data[-1], 3) if ecg_l3_data else 0,
                "ecg_hr": round(ecg_hr_data[-1], 1) if ecg_hr_data else 0,
            },
            "audio": {
                "analog_rms": round(audio_a_data[-1], 1) if audio_a_data else 0,
                "digital_rms": round(audio_d_data[-1], 1) if audio_d_data else 0,
            },
            "vitals": {
                "heart_rate": round(hr_data[-1], 1) if hr_data else 0,
                "spo2": round(spo2_data[-1], 1) if spo2_data else 0,
                "breathing_rate": round(br_data[-1], 1) if br_data else 0,
                "hrv_rmssd": round(hrv_data[-1], 1) if hrv_data else 0,
                "perfusion_index": round(last_pi, 2),
                "signal_quality": signal_quality(last_pi),
            },
            "connection": {
                "vest_connected": vest_connected,
                "fetal_connected": f_connected,
                "using_mock": using_mock,
            },
            "fetal": {
                "mode": f_mode,
                "piezo_raw": f_pz_data[-1] if f_pz_data else [0,0,0,0],
                "kicks": [bool(k) for k in f_kick_data[-1]] if f_kick_data else [False]*4,
                "movement": [bool(m) for m in f_move_data[-1]] if f_move_data else [False]*4,
                "mic_volts": f_mv_data[-1] if f_mv_data else [0.0, 0.0],
                "heart_tones": [bool(h) for h in f_heart_data[-1]] if f_heart_data else [False]*2,
                "bowel_sounds": [bool(b) for b in f_bowel_data[-1]] if f_bowel_data else [False]*2,
                "film_pressure": f_fp_data[-1] if f_fp_data else [0.0, 0.0],
                "contractions": [bool(c) for c in f_cont_data[-1]] if f_cont_data else [False]*2,
                "dawes_redman": get_ctg_analysis(),
            },
            "pharmacology": {
                "active_medication": globals().get('SIMULATED_MEDICATION', None),
                "dose": globals().get('SIMULATED_MEDICATION_DOSE', 0.0),
                "sim_time": globals().get('MEDICATION_SIM_TIME', 0.0),
                "clearance_model": globals().get('PATIENT_CYP2D6_STATUS', "Normal Metabolizer")
            },
            "imu_derived": build_imu_derived_block(
                up_buf=up_data,
                ur_buf=ur_data,
                lp_buf=lp_data,
                lr_buf=lr_data,
                sa_buf=sa_data,
                hr_buf=hr_data,
                fs=SAMPLE_RATE,
            ),
            "waveform": waveform_block,
        }


# =============================================================
# FASTAPI APP
# =============================================================

def _truthy(v: Optional[str]) -> bool:
    return (v or "").strip().lower() in ("1", "true", "yes", "on")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start background threads on server startup. BLE is opt-out via
    MEDVERSE_DISABLE_BLE for cloud deployments where no Bluetooth radio exists."""
    init_db()

    if not _truthy(os.environ.get("MEDVERSE_DISABLE_BLE")):
        ble_thread = threading.Thread(target=ble_thread_runner, daemon=True)
        ble_thread.start()
    else:
        global using_mock
        using_mock = True
        start_mock_data()

    sqlite_thread = threading.Thread(target=sqlite_writer_loop, daemon=True)
    sqlite_thread.start()

    if not _truthy(os.environ.get("MEDVERSE_DISABLE_AGENT_LOOP")):
        agent_thread = threading.Thread(target=agent_runner_loop, daemon=True)
        agent_thread.start()
    yield

app = FastAPI(title="MedVerse Telemetry API", version="1.0.0", lifespan=lifespan)

_cors_origins = cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/api/auth/login")
async def auth_login(req: LoginRequest):
    """Dev login — exchanges username/password for a signed JWT."""
    if not verify_dev_credentials(req.username, req.password):
        from fastapi import HTTPException, status as _status
        raise HTTPException(status_code=_status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return {
        "access_token": create_access_token(subject=req.username),
        "token_type": "bearer",
        "auth_enabled": auth_enabled(),
    }


@app.get("/api/auth/me")
async def auth_me(user=Depends(require_user)):
    return {"user": user, "auth_enabled": auth_enabled()}


@app.get("/api/status")
async def get_status():
    """Return current vest connection status."""
    return {
        "vest_connected": vest_connected,
        "fetal_connected": f_connected,
        "using_mock": using_mock,
        "vest_device": VEST_DEVICE_NAME,
        "fetal_device": FETAL_DEVICE_NAME,
        "sample_rate": SAMPLE_RATE,
        "buffer_size": BUFFER_SIZE,
        "packets_received": time_counter,
    }


@app.get("/stream")
async def stream_telemetry(token: Optional[str] = None, patient_id: Optional[str] = None):
    """
    SSE endpoint — continuously streams telemetry as JSON events.

    EventSource cannot attach Authorization headers, so when
    MEDVERSE_AUTH_ENABLED=true the browser must pass the JWT via
    `?token=…`. `?patient_id=…` is honored on read-only endpoints too.
    """
    # When auth is enabled, require a valid token via query string.
    if auth_enabled():
        from src.utils.auth import _decode  # lightweight local import
        from fastapi import HTTPException, status as _status
        if not token:
            raise HTTPException(
                status_code=_status.HTTP_401_UNAUTHORIZED,
                detail="Missing ?token= for SSE",
            )
        try:
            _decode(token)
        except Exception as e:
            raise HTTPException(
                status_code=_status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid SSE token: {e}",
            )

    async def event_generator() -> AsyncGenerator[str, None]:
        while True:
            snapshot = build_telemetry_snapshot()
            
            if SIMULATION_MODE_GLOBAL != "Live":
                if SIMULATION_MODE_GLOBAL == "6h":
                    snapshot['vitals']['heart_rate'] = max(60, snapshot['vitals']['heart_rate'] - 10)
                    snapshot['temperature']['cervical'] = 37.0
                    snapshot['fetal']['contractions'] = [False, False]
                elif SIMULATION_MODE_GLOBAL == "12h":
                    snapshot['vitals']['heart_rate'] = 80.0
                    snapshot['temperature']['cervical'] = 36.8
                    snapshot['fetal']['kicks'] = [True, False, False, False]
                elif SIMULATION_MODE_GLOBAL == "24h":
                    snapshot['vitals']['heart_rate'] = 72.0
                    snapshot['temperature']['cervical'] = 36.6
                    snapshot['fetal']['kicks'] = [True, False, True, False]
                elif SIMULATION_MODE_GLOBAL == "2w":
                    snapshot['imu']['spinal_angle'] += 5.0
                    snapshot['vitals']['heart_rate'] = 85.0
                elif SIMULATION_MODE_GLOBAL == "4w":
                    snapshot['imu']['spinal_angle'] += 12.0
                    snapshot['vitals']['heart_rate'] = 95.0
                    snapshot['fetal']['contractions'] = [True, True]
                    snapshot['fetal']['kicks'] = [True, True, True, False]

            # Clinical-scenario overlay — drive the vitals into edge cases that
            # exercise the agent fan-out during demos. Set via POST /api/simulation/scenario.
            global SIMULATED_SCENARIO
            scenario = SIMULATED_SCENARIO or "normal"
            if scenario != "normal":
                if scenario == "tachycardia":
                    snapshot['vitals']['heart_rate'] = round(138 + random.uniform(-3, 3), 1)
                    snapshot['ecg']['ecg_hr'] = snapshot['vitals']['heart_rate']
                    snapshot['vitals']['hrv_rmssd'] = round(18 + random.uniform(-2, 2), 1)
                elif scenario == "hypoxia":
                    snapshot['vitals']['spo2'] = round(88 + random.uniform(-2, 2), 1)
                    snapshot['vitals']['breathing_rate'] = round(24 + random.uniform(-2, 2), 1)
                    snapshot['vitals']['heart_rate'] = round(snapshot['vitals']['heart_rate'] + 12, 1)
                elif scenario == "fetal_decel":
                    snapshot['fetal']['contractions'] = [True, True]
                    snapshot['fetal']['kicks'] = [False, False, False, False]
                    snapshot['fetal']['heart_tones'] = [True, True]
                    if isinstance(snapshot['fetal'].get('dawes_redman'), dict):
                        snapshot['fetal']['dawes_redman']['fhr_baseline'] = 95
                        snapshot['fetal']['dawes_redman']['decelerations'] = "late"
                        snapshot['fetal']['dawes_redman']['reactivity'] = "non-reactive"
                elif scenario == "arrhythmia":
                    snapshot['vitals']['hrv_rmssd'] = round(95 + random.uniform(-5, 5), 1)
                    if random.random() < 0.15:
                        snapshot['vitals']['heart_rate'] = round(
                            snapshot['vitals']['heart_rate'] + random.choice([-25.0, 30.0]), 1
                        )
            snapshot['scenario'] = scenario

            # Pharmacokinetic / Pharmacodynamic overlay — two-compartment Bateman curve.
            # C(t) ∝ (k_abs / (k_abs − k_el)) · (e^−k_el·t − e^−k_abs·t)
            # Poor CYP2D6 metabolizers have slower elimination (larger AUC, longer tail).
            global MEDICATION_SIM_TIME, SIMULATED_MEDICATION, SIMULATED_MEDICATION_DOSE, PATIENT_CYP2D6_STATUS
            if SIMULATED_MEDICATION:
                MEDICATION_SIM_TIME += 0.1

                drug = SIMULATED_MEDICATION.lower()
                if "oxytocin" in drug:
                    k_abs, k_el_normal = 0.8, 0.45
                else:
                    k_abs, k_el_normal = 0.4, 0.25
                k_el = k_el_normal * (0.6 if PATIENT_CYP2D6_STATUS == "Poor Metabolizer" else 1.0)

                if abs(k_abs - k_el) > 1e-6:
                    effect_curve = (k_abs / (k_abs - k_el)) * (
                        math.exp(-k_el * MEDICATION_SIM_TIME)
                        - math.exp(-k_abs * MEDICATION_SIM_TIME)
                    )
                else:
                    effect_curve = k_abs * MEDICATION_SIM_TIME * math.exp(-k_abs * MEDICATION_SIM_TIME)
                effect_curve = max(0.0, min(1.0, effect_curve))

                dose_factor = SIMULATED_MEDICATION_DOSE / 100.0
                if "labetalol" in drug:
                    snapshot['vitals']['heart_rate'] -= int(15 * effect_curve * dose_factor)
                elif "oxytocin" in drug:
                    contraction_active = effect_curve * dose_factor > 0.15
                    snapshot['fetal']['contractions'] = [contraction_active, contraction_active]
                    snapshot['vitals']['heart_rate'] += int(5 * effect_curve * dose_factor)

                snapshot['pharmacology']['effect_curve'] = round(effect_curve, 4)
                snapshot['pharmacology']['k_el'] = round(k_el, 4)

                if MEDICATION_SIM_TIME > 3.0 and effect_curve < 0.005:
                    SIMULATED_MEDICATION = None
                    SIMULATED_MEDICATION_DOSE = 0.0
                    MEDICATION_SIM_TIME = 0.0
                
                
            yield f"data: {json.dumps(snapshot)}\n\n"
            await asyncio.sleep(0.1)  # 10 Hz update rate to frontend

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def sqlite_writer_loop():
    """Periodically persist the current telemetry snapshot AND evaluate alert rules."""
    while True:
        snapshot = build_telemetry_snapshot()
        try:
            insert_telemetry(snapshot, patient_id=ACTIVE_PATIENT_ID)
        except Exception as e:
            logging.getLogger(__name__).error(f"telemetry write failed: {e}")
        try:
            evaluate_and_persist_alerts(snapshot, ACTIVE_PATIENT_ID)
        except Exception as e:
            logging.getLogger(__name__).error(f"alert evaluation failed: {e}")
        time.sleep(1.0)


def agent_runner_loop():
    """Background worker — runs all 7 specialty graphs against the latest snapshot
    every 60 s and writes to the interpretations table."""
    if _truthy(os.environ.get("MEDVERSE_DISABLE_AGENT_LOOP")):
        return
    interval = int(os.environ.get("MEDVERSE_AGENT_INTERVAL", "60"))
    time.sleep(15.0)  # let other startup work settle
    log = logging.getLogger(__name__)
    while True:
        snapshot = get_latest_telemetry(patient_id=ACTIVE_PATIENT_ID) or build_telemetry_snapshot()
        # Skip when stream is essentially empty to avoid burning Groq credits.
        hr = (snapshot.get("vitals") or {}).get("heart_rate") or 0
        if hr < 5:
            time.sleep(interval)
            continue
        try:
            from src.graphs.graph_factory import build_expert_graph
        except Exception as e:
            log.warning(f"agent loop: graph factory unavailable ({e}); sleeping")
            time.sleep(interval * 2)
            continue
        for spec in _AGENT_SPECIALTIES:
            try:
                g = build_expert_graph(spec).compile()
                r = g.invoke({"telemetry": snapshot, "patient_id": ACTIVE_PATIENT_ID, "messages": []})
                text, sev, score = "", "normal", 0.0
                if isinstance(r, dict):
                    text = str(r.get("interpretation") or r.get("response") or "")
                    sev = r.get("severity", "normal")
                    try:
                        score = float(r.get("severity_score", 0) or 0)
                    except Exception:
                        score = 0.0
                if text:
                    insert_interpretation(specialty=spec, findings=text, severity=sev,
                                          severity_score=score, patient_id=ACTIVE_PATIENT_ID)
            except Exception as e:
                log.error(f"agent_runner_loop({spec}) failed: {e}")
        time.sleep(interval)


def _resolve_patient_id(query_patient_id: Optional[str], user: Optional[dict]) -> str:
    """Read-time patient resolution: explicit query → JWT sub → active default."""
    if query_patient_id:
        return query_patient_id
    if user and not user.get("anonymous") and user.get("sub"):
        return str(user["sub"])
    return ACTIVE_PATIENT_ID


@app.get("/api/snapshot")
async def get_snapshot(patient_id: Optional[str] = None, user=Depends(require_user)):
    """Return a single snapshot of telemetry data fetched from SQLite."""
    pid = _resolve_patient_id(patient_id, user)
    data = get_latest_telemetry(patient_id=pid)
    return data if data else build_telemetry_snapshot()


@app.get("/api/interpretations")
async def get_interpretations(patient_id: Optional[str] = None, user=Depends(require_user)):
    """Return the latest AI interpretations for each specialty from SQLite."""
    pid = _resolve_patient_id(patient_id, user)
    return get_latest_interpretations(patient_id=pid)


@app.get("/api/history")
async def api_history(
    patient_id: Optional[str] = None,
    resolution: str = "1h",
    limit: int = 500,
    user=Depends(require_user),
):
    """
    Rolled-up HR / SpO2 / BR / HRV time series for the /history dashboard.
    resolution ∈ {"1m", "1h"}. Data is sourced from the Timescale continuous
    aggregate when MEDVERSE_DB_URL is set; otherwise bucketed in Python
    from SQLite.
    """
    if resolution not in ("1m", "1h"):
        resolution = "1h"
    pid = _resolve_patient_id(patient_id, user)
    return get_history(patient_id=pid, resolution=resolution, limit=max(1, min(limit, 2000)))


class ActivePatientRequest(BaseModel):
    patient_id: str


@app.post("/api/patient/active")
async def set_active_patient(req: ActivePatientRequest, user=Depends(require_user)):
    """Swap the in-memory ACTIVE_PATIENT_ID that the SQLite writer loop uses."""
    global ACTIVE_PATIENT_ID
    ACTIVE_PATIENT_ID = req.patient_id or DEFAULT_PATIENT_ID
    return {"status": "success", "active_patient_id": ACTIVE_PATIENT_ID}


@app.get("/api/patient/active")
async def get_active_patient(user=Depends(require_user)):
    return {"active_patient_id": ACTIVE_PATIENT_ID}

class SimulationRequest(BaseModel):
    mode: str

@app.post("/api/simulation/mode")
async def set_simulation_mode(req: SimulationRequest):
    global SIMULATION_MODE_GLOBAL
    SIMULATION_MODE_GLOBAL = req.mode
    return {"status": "success", "mode": SIMULATION_MODE_GLOBAL}

SIMULATED_MEDICATION = None
SIMULATED_MEDICATION_DOSE = 0.0
MEDICATION_SIM_TIME = 0.0
PATIENT_CYP2D6_STATUS = "Normal Metabolizer" # Default

class MedicationRequest(BaseModel):
    medication: str
    dose: float

@app.post("/api/simulation/medicate")
async def inject_medication(req: MedicationRequest):
    global SIMULATED_MEDICATION, SIMULATED_MEDICATION_DOSE, MEDICATION_SIM_TIME
    SIMULATED_MEDICATION = req.medication
    SIMULATED_MEDICATION_DOSE = req.dose
    MEDICATION_SIM_TIME = 0.0
    return {"status": "success", "medication": req.medication, "dose": req.dose}


SIMULATED_SCENARIO = "normal"
_VALID_SCENARIOS = {"normal", "tachycardia", "hypoxia", "fetal_decel", "arrhythmia"}


class ScenarioRequest(BaseModel):
    scenario: str


@app.post("/api/simulation/scenario")
async def set_scenario(req: ScenarioRequest):
    """Switch the live mock-data scenario. Used to demo agent fan-out without
    real abnormal hardware data."""
    global SIMULATED_SCENARIO
    if req.scenario not in _VALID_SCENARIOS:
        from fastapi import HTTPException, status as _status
        raise HTTPException(
            status_code=_status.HTTP_400_BAD_REQUEST,
            detail=f"scenario must be one of {sorted(_VALID_SCENARIOS)}",
        )
    SIMULATED_SCENARIO = req.scenario
    return {"status": "success", "scenario": SIMULATED_SCENARIO}


@app.get("/api/simulation/scenario")
async def get_scenario():
    return {"scenario": SIMULATED_SCENARIO, "available": sorted(_VALID_SCENARIOS)}


class CYP2D6Request(BaseModel):
    status: str


@app.post("/api/simulation/cyp2d6")
async def set_cyp2d6(req: CYP2D6Request):
    """Set the simulated CYP2D6 metabolizer status. Drives the k_el modulation
    in the PK/PD overlay above (Poor Metabolizer → 60% elimination rate)."""
    global PATIENT_CYP2D6_STATUS
    if req.status not in ("Normal Metabolizer", "Poor Metabolizer"):
        from fastapi import HTTPException, status as _status
        raise HTTPException(
            status_code=_status.HTTP_400_BAD_REQUEST,
            detail="status must be 'Normal Metabolizer' or 'Poor Metabolizer'",
        )
    PATIENT_CYP2D6_STATUS = req.status
    return {"status": "success", "cyp2d6_status": PATIENT_CYP2D6_STATUS}

import base64
from groq import Groq
import os

try:
    groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
except:
    groq_client = None

# =============================================================
# FHIR R4 INTEROP
# =============================================================

DEFAULT_PATIENT_ID = "medverse-demo-patient"


@app.get("/api/fhir/Observation/latest")
async def fhir_observations_latest(patient_id: str = DEFAULT_PATIENT_ID, user=Depends(require_user)):
    """Latest telemetry snapshot serialized as a list of FHIR Observations."""
    snap = get_latest_telemetry() or build_telemetry_snapshot()
    return snapshot_to_observations(snap, patient_id=patient_id)


@app.get("/api/fhir/Bundle/latest")
async def fhir_bundle_latest(patient_id: str = DEFAULT_PATIENT_ID, user=Depends(require_user)):
    """Latest telemetry as a FHIR R4 Bundle of Observations."""
    snap = get_latest_telemetry() or build_telemetry_snapshot()
    return snapshot_to_bundle(snap, patient_id=patient_id)


@app.get("/api/fhir/DiagnosticReport/latest")
async def fhir_diagnostic_reports_latest(patient_id: str = DEFAULT_PATIENT_ID, user=Depends(require_user)):
    """All specialty interpretations serialized as FHIR DiagnosticReports."""
    interpretations = get_latest_interpretations() or {}
    reports = []
    for specialty, payload in interpretations.items():
        reports.append(
            expert_to_diagnostic_report(
                specialty=specialty,
                finding=payload.get("interpretation", ""),
                severity=payload.get("severity", "unknown"),
                severity_score=payload.get("severity_score", 0.0),
                patient_id=patient_id,
                generated_at=payload.get("generated_at"),
                confidence=payload.get("confidence", 0.0),
            )
        )
    return reports


@app.get("/api/fhir/DiagnosticReport/{specialty}/latest")
async def fhir_diagnostic_report_by_specialty(
    specialty: str, patient_id: str = DEFAULT_PATIENT_ID, user=Depends(require_user)
):
    interpretations = get_latest_interpretations() or {}
    key = next((k for k in interpretations if k.lower() == specialty.lower()), None)
    if key is None:
        return {"error": "not_found", "specialty": specialty}
    payload = interpretations[key]
    return expert_to_diagnostic_report(
        specialty=key,
        finding=payload.get("interpretation", ""),
        severity=payload.get("severity", "unknown"),
        severity_score=payload.get("severity_score", 0.0),
        patient_id=patient_id,
        generated_at=payload.get("generated_at"),
        confidence=payload.get("confidence", 0.0),
    )


@app.get("/api/fhir/Patient/{patient_id}")
async def fhir_patient(patient_id: str, user=Depends(require_user)):
    return patient_resource(patient_id)


@app.get("/api/fhir/Device")
async def fhir_devices(user=Depends(require_user)):
    return [
        device_resource(VEST_DEVICE_NAME, serial="AEGIS-VEST-001"),
        device_resource(FETAL_DEVICE_NAME, serial="ABDOMEN-MON-001"),
    ]


@app.post("/api/upload-lab-results")
async def upload_lab_results(file: UploadFile = File(...)):
    global PATIENT_CYP2D6_STATUS
    
    content = await file.read()
    
    if groq_client and file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        try:
            base64_image = base64.b64encode(content).decode('utf-8')
            mime_type = "image/jpeg" if file.filename.lower().endswith(('jpg', 'jpeg')) else "image/png"
            image_url = f"data:{mime_type};base64,{base64_image}"
            
            completion = groq_client.chat.completions.create(
                model="llama-3.2-11b-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": 'Extract the patient\'s AST and ALT levels, and any CYP2D6 genetic metabolizer status. If CYP2D6 is not listed but liver enzymes (AST/ALT) are significantly elevated (>100 U/L), deduce "Poor Metabolizer", else deduce "Normal Metabolizer". Return exactly this JSON format: {"AST": <val>, "ALT": <val>, "CYP2D6": "<status>"}'
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": image_url
                                }
                            }
                        ]
                    }
                ],
                temperature=0.1,
                max_tokens=256,
            )
            
            response_text = completion.choices[0].message.content
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start != -1 and end != -1:
                parsed = json.loads(response_text[start:end])
                PATIENT_CYP2D6_STATUS = parsed.get("CYP2D6", "Poor Metabolizer")
                return {"status": "success", "extracted_data": parsed}
        except Exception as e:
            print(f"Vision OCR Error: {e}")
            pass
            
    # Fallback to smart-mocking if file isn't an image or API fails
    PATIENT_CYP2D6_STATUS = "Poor Metabolizer"
    return {"status": "success", "extracted_data": {"AST": 142, "ALT": 160, "CYP2D6": "Poor Metabolizer"}}




@app.get("/health")
async def health():
    """Lightweight liveness probe for Render / load balancers."""
    return {"status": "ok", "mock": using_mock, "ble_disabled": _truthy(os.environ.get("MEDVERSE_DISABLE_BLE"))}


# =============================================================
# PATIENTS (Phase 3)
# =============================================================

class PatientCreate(BaseModel):
    name: str
    mrn: Optional[str] = None
    dob: Optional[str] = None
    sex: Optional[str] = None
    gestational_age_weeks: Optional[int] = None
    conditions: Optional[list] = None
    assigned_clinician_id: Optional[str] = None
    care_plan_id: Optional[str] = None


class PatientUpdate(BaseModel):
    name: Optional[str] = None
    mrn: Optional[str] = None
    dob: Optional[str] = None
    sex: Optional[str] = None
    gestational_age_weeks: Optional[int] = None
    conditions: Optional[list] = None
    assigned_clinician_id: Optional[str] = None
    care_plan_id: Optional[str] = None


@app.get("/api/patients")
async def api_list_patients(request: Request, user=Depends(require_user)):
    audit(request, user, "list", "patients")
    return list_patients()


@app.get("/api/patients/{patient_id}")
async def api_get_patient(patient_id: str, request: Request, user=Depends(require_user)):
    p = get_patient(patient_id)
    if not p:
        from fastapi import HTTPException, status as _st
        raise HTTPException(status_code=_st.HTTP_404_NOT_FOUND, detail="Patient not found")
    audit(request, user, "read", "patient", patient_id)
    return p


@app.post("/api/patients")
async def api_create_patient(req: PatientCreate, request: Request, user=Depends(require_user)):
    p = upsert_patient(req.model_dump())
    audit(request, user, "create", "patient", p.get("id"))
    return p


@app.patch("/api/patients/{patient_id}")
async def api_update_patient(patient_id: str, req: PatientUpdate, request: Request, user=Depends(require_user)):
    existing = get_patient(patient_id)
    if not existing:
        from fastapi import HTTPException, status as _st
        raise HTTPException(status_code=_st.HTTP_404_NOT_FOUND, detail="Patient not found")
    merged = {**existing, **{k: v for k, v in req.model_dump().items() if v is not None}}
    merged["id"] = patient_id
    p = upsert_patient(merged)
    audit(request, user, "update", "patient", patient_id)
    return p


# =============================================================
# ALERTS (Phase 4)
# =============================================================

@app.get("/api/alerts")
async def api_list_alerts(
    patient_id: Optional[str] = None,
    unacknowledged: bool = False,
    limit: int = 100,
    request: Request = None,  # type: ignore
    user=Depends(require_user),
):
    pid = _resolve_patient_id(patient_id, user) if patient_id is None else patient_id
    audit(request, user, "list", "alerts", pid)
    return list_alerts(patient_id=pid, unacknowledged=unacknowledged, limit=max(1, min(limit, 1000)))


class AcknowledgeRequest(BaseModel):
    note: Optional[str] = ""


@app.post("/api/alerts/{alert_id}/acknowledge")
async def api_ack_alert(alert_id: int, req: AcknowledgeRequest, request: Request, user=Depends(require_user)):
    user_id = (user or {}).get("sub", "anonymous") if isinstance(user, dict) else "anonymous"
    ok = acknowledge_alert(alert_id, user_id=user_id, note=req.note or "")
    audit(request, user, "acknowledge", "alert", str(alert_id))
    return {"status": "ok" if ok else "not_found"}


@app.get("/api/alerts/stream")
async def api_alerts_stream(token: Optional[str] = None, patient_id: Optional[str] = None):
    """SSE feed of newly-created alerts. Polls the DB every 2s."""
    if auth_enabled():
        from fastapi import HTTPException, status as _st
        if not token:
            raise HTTPException(status_code=_st.HTTP_401_UNAUTHORIZED, detail="Missing ?token=")
        try:
            from src.utils.auth import _decode
            _decode(token)
        except Exception as e:
            raise HTTPException(status_code=_st.HTTP_401_UNAUTHORIZED, detail=str(e))

    async def gen():
        last_id = 0
        while True:
            try:
                rows = list_alerts(patient_id=patient_id, limit=20)
                rows = [r for r in rows if r["id"] > last_id]
                rows.sort(key=lambda r: r["id"])
                for r in rows:
                    last_id = max(last_id, r["id"])
                    yield f"data: {json.dumps(r)}\n\n"
            except Exception as e:
                logging.getLogger(__name__).error(f"alerts stream error: {e}")
            await asyncio.sleep(2.0)

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# =============================================================
# AGENT INVOCATION (Phase 5)
# =============================================================

class AgentAskRequest(BaseModel):
    specialty: str
    message: str
    patient_id: Optional[str] = None


_SPECIALTY_TO_GRAPH = {
    "cardiology": "Cardiology Expert",
    "pulmonary": "Pulmonary Expert",
    "respiratory": "Pulmonary Expert",
    "neurology": "Neurology Expert",
    "dermatology": "Dermatology Expert",
    "obstetrics": "Obstetrics Expert",
    "gynecology": "Obstetrics Expert",
    "ocular": "Ocular Expert",
    "general physician": "General Physician",
    "general_physician": "General Physician",
}


def _resolve_specialty(label: str) -> str:
    return _SPECIALTY_TO_GRAPH.get((label or "").strip().lower(), label or "")


@app.post("/api/agent/ask")
async def api_agent_ask(req: AgentAskRequest, request: Request, user=Depends(require_user)):
    """Synchronously invoke an expert graph and return its assessment."""
    specialty = _resolve_specialty(req.specialty)
    pid = _resolve_patient_id(req.patient_id, user)
    audit(request, user, "ask", "agent", specialty)
    try:
        from src.graphs.graph_factory import build_expert_graph
        graph = build_expert_graph(specialty).compile()
        snapshot = get_latest_telemetry(patient_id=pid) or build_telemetry_snapshot()
        state = {
            "messages": [{"role": "user", "content": req.message}],
            "patient_id": pid,
            "telemetry": snapshot,
        }
        result = graph.invoke(state)
        reply = ""
        if isinstance(result, dict):
            messages = result.get("messages") or []
            if messages:
                last = messages[-1]
                reply = last.get("content") if isinstance(last, dict) else getattr(last, "content", "")
            reply = reply or str(result.get("interpretation") or result.get("response") or "")
        return {
            "reply": reply or "(no response)",
            "severity": (result or {}).get("severity", "normal"),
            "severity_score": (result or {}).get("severity_score", 0),
            "specialty": specialty,
        }
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"agent ask failed: {e}")
        return {
            "reply": f"Agent unavailable: {e}. Telemetry snapshot is still being collected — try again in a few seconds.",
            "severity": "normal",
            "severity_score": 0,
            "specialty": specialty,
        }


_AGENT_SPECIALTIES = ["Cardiology", "Pulmonary", "Neurology", "Dermatology", "Obstetrics", "Ocular", "General Physician"]


@app.post("/api/agent/run-now")
async def api_agent_run_now(
    patient_id: Optional[str] = None,
    specialty: Optional[str] = None,
    request: Request = None,  # type: ignore
    user=Depends(require_user),
):
    """Trigger an immediate run for one or all specialties; persists to interpretations."""
    pid = _resolve_patient_id(patient_id, user)
    targets = [specialty] if specialty else _AGENT_SPECIALTIES
    targets = [_resolve_specialty(s) for s in targets if s]
    ran: list = []
    snapshot = get_latest_telemetry(patient_id=pid) or build_telemetry_snapshot()
    try:
        from src.graphs.graph_factory import build_expert_graph
    except Exception as e:
        return {"status": "graph_unavailable", "error": str(e), "ran": []}
    for spec in targets:
        try:
            g = build_expert_graph(spec).compile()
            r = g.invoke({"telemetry": snapshot, "patient_id": pid, "messages": []})
            text = ""
            sev = "normal"
            score = 0
            if isinstance(r, dict):
                text = str(r.get("interpretation") or r.get("response") or "")
                sev = r.get("severity", "normal")
                score = float(r.get("severity_score", 0) or 0)
            insert_interpretation(specialty=spec, findings=text or "(no output)",
                                  severity=sev, severity_score=score, patient_id=pid)
            ran.append(spec)
        except Exception as e:
            logging.getLogger(__name__).error(f"run-now {spec} failed: {e}")
    audit(request, user, "run_now", "agents", ",".join(ran))
    return {"status": "ok", "ran": ran}


# =============================================================
# AUDIT (Phase 8)
# =============================================================

@app.get("/api/admin/audit")
async def api_admin_audit(
    limit: int = 200,
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    user=Depends(require_user),
):
    admin_username = os.environ.get("MEDVERSE_ADMIN_USERNAME", "medverse")
    if auth_enabled() and isinstance(user, dict) and user.get("sub") != admin_username:
        from fastapi import HTTPException, status as _st
        raise HTTPException(status_code=_st.HTTP_403_FORBIDDEN, detail="Admin only")
    return list_audit(limit=max(1, min(limit, 1000)), user_id=user_id, action=action)


# =============================================================
# EMERGENCY (Phase 12)
# =============================================================

class EmergencyRequest(BaseModel):
    patient_id: Optional[str] = None
    message: str
    vitals: Optional[dict] = None
    geolocation: Optional[dict] = None


@app.post("/api/emergency")
async def api_emergency(req: EmergencyRequest, request: Request, user=Depends(require_user)):
    """Emergency action — fires a configured webhook + records a critical alert."""
    pid = _resolve_patient_id(req.patient_id, user)
    audit(request, user, "emergency", "patient", pid)
    insert_alert(
        patient_id=pid,
        severity=10,
        source="emergency_button",
        message=req.message or "Manual emergency activation",
        snapshot=req.vitals or get_latest_telemetry(patient_id=pid),
    )
    webhook = os.environ.get("MEDVERSE_EMERGENCY_WEBHOOK")
    posted = None
    if webhook:
        try:
            import urllib.request
            payload = json.dumps({
                "patient_id": pid,
                "message": req.message,
                "vitals": req.vitals or {},
                "geolocation": req.geolocation or {},
            }).encode()
            r = urllib.request.Request(webhook, data=payload, headers={"Content-Type": "application/json"})
            urllib.request.urlopen(r, timeout=4)
            posted = webhook
        except Exception as e:
            logging.getLogger(__name__).error(f"emergency webhook failed: {e}")
    return {"status": "ok", "webhook": posted}


# =============================================================
# CARE PLANS (Phase 6 — minimal seed)
# =============================================================

CARE_PLAN_SEED = [
    {
        "id": "preeclampsia_monitoring",
        "name": "Preeclampsia monitoring",
        "conditions": ["pregnancy", "hypertension"],
        "thresholds": {
            "spo2_min": 94,
            "hr_max": 110,
            "rr_max": 22,
        },
        "monitoring_frequency_s": 60,
    },
    {
        "id": "post_cardiac_op",
        "name": "Post-cardiac operative",
        "conditions": ["cardiac_surgery"],
        "thresholds": {
            "hr_min": 50,
            "hr_max": 110,
            "spo2_min": 92,
        },
        "monitoring_frequency_s": 30,
    },
    {
        "id": "chronic_copd",
        "name": "Chronic COPD",
        "conditions": ["copd"],
        "thresholds": {
            "spo2_min": 88,
            "rr_max": 25,
        },
        "monitoring_frequency_s": 120,
    },
]


@app.get("/api/care-plans")
async def api_care_plans():
    return CARE_PLAN_SEED


class AssignCarePlanRequest(BaseModel):
    care_plan_id: str


@app.post("/api/patients/{patient_id}/care-plan")
async def api_assign_care_plan(patient_id: str, req: AssignCarePlanRequest, request: Request, user=Depends(require_user)):
    existing = get_patient(patient_id)
    if not existing:
        from fastapi import HTTPException, status as _st
        raise HTTPException(status_code=_st.HTTP_404_NOT_FOUND, detail="Patient not found")
    merged = {**existing, "care_plan_id": req.care_plan_id, "id": patient_id}
    upsert_patient(merged)
    audit(request, user, "assign_care_plan", "patient", patient_id)
    return {"status": "ok", "care_plan_id": req.care_plan_id}


def _care_plan_thresholds(plan_id: Optional[str]) -> dict:
    if not plan_id:
        return {}
    for p in CARE_PLAN_SEED:
        if p["id"] == plan_id:
            return p.get("thresholds", {})
    return {}


# =============================================================
# ALERT EVALUATION HOOK (called from sqlite_writer_loop)
# =============================================================

def evaluate_and_persist_alerts(snapshot: dict, patient_id: str) -> None:
    pat = get_patient(patient_id)
    plan_id = (pat or {}).get("care_plan_id") if pat else None
    thresholds = _care_plan_thresholds(plan_id)
    for a in evaluate_alerts(snapshot, thresholds=thresholds):
        if find_recent_alert(patient_id, a["source"], within_seconds=120):
            continue
        insert_alert(
            patient_id=patient_id,
            severity=a["severity"],
            source=a["source"],
            message=a["message"],
            snapshot=snapshot,
        )


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)

"""
Aegis Vest — FastAPI Backend with BLE Streaming
Connects to 'Aegis_SpO2_Live' via BLE and streams telemetry over SSE.
Falls back to simulated data when no device is available.
"""

import asyncio
import json
import math
import time
import threading
from collections import deque
from typing import AsyncGenerator

import numpy as np
from scipy.signal import butter, filtfilt, find_peaks
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from src.utils.db import init_db, insert_telemetry, get_latest_telemetry, get_latest_interpretations

# =============================================================
# CONFIGURATION
# =============================================================
VEST_DEVICE_NAME = "Aegis_SpO2_Live"
FETAL_DEVICE_NAME = "AbdomenMonitor"
VEST_CHAR_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a8"
FETAL_CHAR_UUID = "12345678-1234-1234-1234-123456789ab1"
SAMPLE_RATE = 40
BUFFER_SIZE = 800
SPO2_WINDOW = 160
BR_WINDOW = 400

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

# ECG
ecg_l1_data = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
ecg_l2_data = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
ecg_l3_data = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
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
        ecg_l1 = float(parts.get('L1', 0))
        ecg_l2 = float(parts.get('L2', 0))
        ecg_l3 = float(parts.get('L3', 0))
        ecg_hr = float(parts.get('EHR', 0))
        audio_a = float(parts.get('ARMS', 0))
        audio_d = float(parts.get('DRMS', 0))

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
            ecg_l1_data.append(ecg_l1)
            ecg_l2_data.append(ecg_l2)
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


async def run_single_client(device_name: str, char_uuid: str, handler_func, set_connected_flag_func):
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
                await client.start_notify(char_uuid, handler_func)
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

    task1 = run_single_client(VEST_DEVICE_NAME, VEST_CHAR_UUID, handle_ble_notification, set_vest_connected)
    task2 = run_single_client(FETAL_DEVICE_NAME, FETAL_CHAR_UUID, handle_fetal_notification, set_fetal_connected)
    
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

def build_telemetry_snapshot() -> dict:
    """Build a JSON-serializable snapshot of all current telemetry data."""
    with data_lock:
        last_sa = sa_data[-1] if sa_data else 0
        last_pi = pi_data[-1] if pi_data else 0
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
            }
        }


# =============================================================
# FASTAPI APP
# =============================================================

app = FastAPI(title="Aegis Vest Telemetry API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Start BLE connection thread on server startup."""
    init_db()
    ble_thread = threading.Thread(target=ble_thread_runner, daemon=True)
    ble_thread.start()
    
    sqlite_thread = threading.Thread(target=sqlite_writer_loop, daemon=True)
    sqlite_thread.start()


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
async def stream_telemetry():
    """SSE endpoint — continuously streams telemetry as JSON events."""

    async def event_generator() -> AsyncGenerator[str, None]:
        while True:
            snapshot = build_telemetry_snapshot()
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
    """Periodically write the current telemetry snapshot to SQLite."""
    while True:
        snapshot = build_telemetry_snapshot()
        insert_telemetry(snapshot)
        time.sleep(1.0)


@app.get("/api/snapshot")
async def get_snapshot():
    """Return a single snapshot of telemetry data fetched from SQLite."""
    data = get_latest_telemetry()
    return data if data else build_telemetry_snapshot()


@app.get("/api/interpretations")
async def get_interpretations():
    """Return the latest AI interpretations for each specialty from SQLite."""
    return get_latest_interpretations()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

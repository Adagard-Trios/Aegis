import asyncio
import threading
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.gridspec as gridspec
from collections import deque
from bleak import BleakClient, BleakScanner
import numpy as np
from scipy.signal import butter, filtfilt, find_peaks

# =============================================================
# CONFIGURATION
# =============================================================
DEVICE_NAME  = "Aegis_SpO2_Live"
CHAR_UUID    = "beb5483e-36e1-4688-b7f5-ea07361b26a8"
SAMPLE_RATE  = 40
BUFFER_SIZE  = 800
SPO2_WINDOW  = 160
BR_WINDOW    = 400

data_lock = threading.Lock()

# =============================================================
# BUFFERS
# =============================================================
x_data     = deque([0]   * BUFFER_SIZE, maxlen=BUFFER_SIZE)

# PPG
ir1_data   = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
red1_data  = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
ir2_data   = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
red2_data  = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
ira_data   = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
reda_data  = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)

# PPG onboard temps
ppg_t1_data = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
ppg_t2_data = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)

# DS18B20 skin temps
tl_data    = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
tr_data    = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
tc_data    = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)

# IMU
up_data    = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)  # upper pitch
ur_data    = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)  # upper roll
lp_data    = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)  # lower pitch
lr_data    = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)  # lower roll
sa_data    = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)  # spinal angle
pp_data    = deque([0]   * BUFFER_SIZE, maxlen=BUFFER_SIZE)  # poor posture flag

# ECG 
ecg_l1_data = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
ecg_l2_data = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
ecg_l3_data = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
ecg_hr_data = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)

# Audio
audio_a_data = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
audio_d_data = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)

# Derived
hr_data    = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
spo2_data  = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
br_data    = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
hrv_data   = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
pi_data    = deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)

time_counter = 0

# =============================================================
# SIGNAL PROCESSING
# =============================================================
def bandpass_filter(data, lowcut, highcut, fs, order=3):
    nyq  = fs / 2.0
    low  = max(0.001, min(lowcut  / nyq, 0.999))
    high = max(0.001, min(highcut / nyq, 0.999))
    if low >= high:
        return np.array(data)
    try:
        b, a = butter(order, [low, high], btype='band')
        return filtfilt(b, a, np.array(data))
    except Exception:
        return np.array(data)

def lowpass_filter(data, cutoff, fs, order=3):
    nyq  = fs / 2.0
    norm = min(cutoff / nyq, 0.999)
    try:
        b, a = butter(order, norm, btype='low')
        return filtfilt(b, a, np.array(data))
    except Exception:
        return np.array(data)

def calculate_spo2(ir_buf, red_buf):
    SPO2_TABLE = [
        100, 100, 100, 100, 99, 99, 99, 98, 98, 98,
         97,  97,  96,  96,  95, 95, 94, 94, 93, 93,
         92,  92,  91,  90,  89, 88, 86, 85, 83, 81
    ]
    ir  = np.array(ir_buf[-SPO2_WINDOW:],  dtype=float)
    red = np.array(red_buf[-SPO2_WINDOW:], dtype=float)
    if len(ir) < SPO2_WINDOW or np.mean(ir) < 1000:
        return 0.0
    ir_ac  = np.std(ir);  ir_dc  = np.mean(ir)
    red_ac = np.std(red); red_dc = np.mean(red)
    if ir_dc == 0 or red_dc == 0 or ir_ac < 10:
        return 0.0
    R     = (red_ac / red_dc) / (ir_ac / ir_dc)
    index = max(0, min(int((R - 0.4) * 10), len(SPO2_TABLE) - 1))
    return float(SPO2_TABLE[index])

def calculate_heart_rate(ir_buf):
    ir = np.array(ir_buf, dtype=float)
    if len(ir) < SAMPLE_RATE * 4:
        return 0.0, []
    filtered = bandpass_filter(ir, 0.5, 4.0, SAMPLE_RATE)
    min_dist = int(SAMPLE_RATE * 60 / 180)
    peaks, _ = find_peaks(-filtered, distance=min_dist,
                           prominence=np.std(filtered) * 0.5)
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
    peaks, _ = find_peaks(-filtered, distance=min_dist,
                           prominence=np.std(filtered) * 0.5)
    if len(peaks) < 4:
        return 0.0
    rr  = np.diff(peaks) / SAMPLE_RATE * 1000
    return round(np.sqrt(np.mean(np.diff(rr) ** 2)), 1)

def calculate_breathing_rate(ir_buf):
    ir = np.array(ir_buf[-BR_WINDOW:], dtype=float)
    if len(ir) < BR_WINDOW:
        return 0.0
    br_signal = lowpass_filter(ir, 0.5, SAMPLE_RATE)
    min_dist  = int(SAMPLE_RATE * 60 / 40)
    peaks, _  = find_peaks(br_signal, distance=min_dist,
                            prominence=np.std(br_signal) * 0.3)
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
    if pi == 0:   return "No contact"
    if pi < 0.2:  return "Poor"
    if pi < 0.5:  return "Fair"
    if pi < 2.0:  return "Good"
    return "Excellent"

def posture_label(sa):
    if abs(sa) < 5:   return "Good posture", '#2ecc71'
    if abs(sa) < 15:  return "Moderate",     '#f39c12'
    return "Poor posture!", '#e74c3c'

# =============================================================
# BLE HANDLER
# =============================================================
def handle_ble_notification(sender, data):
    global time_counter
    try:
        decoded = data.decode('utf-8').strip()
        parts = {}

        # Safely parse the data into a dictionary
        for p in decoded.split(','):
            if ':' in p:
                key, value = p.split(':', 1)
                parts[key] = value

        # Debugging: Log raw data and parsed parts
        print(f"DEBUG: Raw data: {decoded}")
        print(f"DEBUG: Parsed parts: {parts}")

        # PPG
        ir1 = float(parts.get('IR1', 0))
        red1 = float(parts.get('Red1', 0))
        ir2 = float(parts.get('IR2', 0))
        red2 = float(parts.get('Red2', 0))
        ira = float(parts.get('IRA', 0))
        reda = float(parts.get('RedA', 0))
        t1 = float(parts.get('T1', 0))
        t2 = float(parts.get('T2', 0))

        # DS18B20 skin temps
        tl = float(parts.get('TL', 0))
        tr = float(parts.get('TR', 0))
        tc = float(parts.get('TC', 0))

        # IMU
        up = float(parts.get('UP', 0))
        ur = float(parts.get('UR', 0))
        lp = float(parts.get('LP', 0))
        lr = float(parts.get('LR', 0))
        sa = float(parts.get('SA', 0))
        pp = int(parts.get('PP', 0))

        # ECG data
        ecg_l1 = float(parts.get('L1', 0))
        ecg_l2 = float(parts.get('L2', 0))
        ecg_l3 = float(parts.get('L3', 0))
        ecg_hr = float(parts.get('EHR', 0))

        # Audio data
        audio_a = float(parts.get('ARMS', 0))  # Updated key to match ESP32 payload
        audio_d = float(parts.get('DRMS', 0))  # Updated key to match ESP32 payload

        # Debugging: Log parsed ECG and Audio values
        print(f"DEBUG: ECG L1={ecg_l1}, L2={ecg_l2}, L3={ecg_l3}, HR={ecg_hr}")
        print(f"DEBUG: Audio ARMS={audio_a}, DRMS={audio_d}")

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
            ur_data.append(ur)
            lp_data.append(lp)
            lr_data.append(lr)
            sa_data.append(sa)
            pp_data.append(pp)

            # Append ECG data
            ecg_l1_data.append(ecg_l1)
            ecg_l2_data.append(ecg_l2)
            ecg_l3_data.append(ecg_l3)
            ecg_hr_data.append(ecg_hr)
            
            # Append Audio data
            audio_a_data.append(audio_a)
            audio_d_data.append(audio_d)

            # Ensure valid data before calculations
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

        pl, _ = posture_label(sa)
        posture_icon = "POOR" if pp else "OK"

        # Full comprehensive output
        print(f"\n{'='*120}")
        print(f"[AEGIS TELEMETRY] Packet #{time_counter}")
        print(f"{'='*120}")
        print(f"PPG SENSORS (Optical)")
        print(f"  Sensor 1: IR={ir1:7.0f}   Red={red1:7.0f}")
        print(f"  Sensor 2: IR={ir2:7.0f}   Red={red2:7.0f}")
        print(f"  Average:  IRA={ira:7.0f}   RedA={reda:7.0f}")
        print(f"  Onboard:  T1={t1:6.2f}°C  T2={t2:6.2f}°C")
        print(f"{'─'*120}")
        print(f"TEMPERATURE (Skin)")
        print(f"  Left Axilla:    {tl:6.2f}°C")
        print(f"  Right Axilla:   {tr:6.2f}°C")
        print(f"  Cervical (C7):  {tc:6.2f}°C")
        print(f"{'─'*120}")
        print(f"IMU (Motion & Posture)")
        print(f"  Upper Body:  Pitch={up:7.2f}°  Roll={ur:7.2f}°")
        print(f"  Lower Body:  Pitch={lp:7.2f}°  Roll={lr:7.2f}°")
        print(f"  Spinal Angle (SA): {sa:7.2f}°")
        print(f"  Posture Status: [{posture_icon}] {'🚨 POOR POSTURE' if pp else '✓ Good'}")
        print(f"{'─'*120}")
        print(f"ECG (3-Lead)")
        print(f"  Lead I:   {ecg_l1:8.1f} mV")
        print(f"  Lead II:  {ecg_l2:8.1f} mV")
        print(f"  Lead III: {ecg_l3:8.1f} mV")
        print(f"  ECG HR:   {ecg_hr:8.1f} BPM")
        print(f"{'─'*120}")
        print(f"AUDIO")
        print(f"  Analog RMS:  {audio_a:8.1f}")
        print(f"  Digital RMS: {audio_d:8.1f}")
        print(f"{'─'*120}")
        print(f"DERIVED METRICS")
        print(f"  Heart Rate (PPG):     {bpm:6.1f} BPM")
        print(f"  SpO2 (Oxygen):        {spo2:6.1f} %")
        print(f"  Breathing Rate:       {br:6.1f} br/min")
        print(f"  HRV (RMSSD):          {hrv:6.1f} ms")
        print(f"  Perfusion Index:      {pi:6.2f} %")
        print(f"  Signal Quality:       {signal_quality(pi)}")
        print(f"{'='*120}\n")

    except Exception as e:
        print(f"❌ Parse error: {e}")
        print(f"Raw data: {data}\n")

async def run_ble_client():
    print(f"Scanning for '{DEVICE_NAME}'...")
    device = await BleakScanner.find_device_by_name(DEVICE_NAME, timeout=10.0)
    if not device:
        print("FAIL: Device not found.")
        return
    print(f"Found at {device.address}. Connecting...")
    try:
        async with BleakClient(device) as client:
            if client.is_connected:
                print("Connected! Streaming full telemetry...\n")
                await client.start_notify(CHAR_UUID, handle_ble_notification)
                while True:
                    await asyncio.sleep(1)
    except Exception as e:
        print(f"BLE error: {e}")

def ble_thread_runner():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_ble_client())

# =============================================================
# COLOR HELPERS
# =============================================================
def c_spo2(v):
    if v >= 95: return '#2ecc71'
    if v >= 90: return '#f39c12'
    return '#e74c3c'

def c_hr(v):
    if 50 <= v <= 100: return '#2ecc71'
    if 40 <= v <= 120: return '#f39c12'
    return '#e74c3c'

def c_br(v):
    if 12 <= v <= 20: return '#2ecc71'
    if 8  <= v <= 25: return '#f39c12'
    return '#e74c3c'

def c_temp(v):
    if 36.0 <= v <= 37.5: return '#2ecc71'
    if 35.0 <= v <= 38.5: return '#f39c12'
    return '#e74c3c'

# =============================================================
# DASHBOARD
# =============================================================
def main():
    ble_thread = threading.Thread(target=ble_thread_runner, daemon=True)
    ble_thread.start()

    fig = plt.figure(figsize=(18, 13))
    fig.patch.set_facecolor('#0d0d0d')
    fig.canvas.manager.set_window_title('Aegis Vest — Full Telemetry Dashboard')

    # 5 rows x 4 cols
    gs = gridspec.GridSpec(5, 4, figure=fig, hspace=0.55, wspace=0.38)

    # Row 0: Raw PPG (full width)
    ax_ppg   = fig.add_subplot(gs[0, :])
    # Row 1: HR | SpO2 | BR | HRV
    ax_hr    = fig.add_subplot(gs[1, 0])
    ax_spo2  = fig.add_subplot(gs[1, 1])
    ax_br    = fig.add_subplot(gs[1, 2])
    ax_hrv   = fig.add_subplot(gs[1, 3])
    # Row 2: PI | PPG onboard temp | Skin temp L/R | Skin temp C
    ax_pi    = fig.add_subplot(gs[2, 0])
    ax_ptemp = fig.add_subplot(gs[2, 1])
    ax_stemp = fig.add_subplot(gs[2, 2])
    ax_ctemp = fig.add_subplot(gs[2, 3])
    # Row 3: Spinal angle (spans 2) | Upper IMU | Lower IMU
    ax_sa    = fig.add_subplot(gs[3, :2])
    ax_uimu  = fig.add_subplot(gs[3, 2])
    ax_limu  = fig.add_subplot(gs[3, 3])
    # Row 4: Filtered PPG (full width)
    ax_filt  = fig.add_subplot(gs[4, :])

    all_axes = [ax_ppg, ax_hr, ax_spo2, ax_br, ax_hrv,
                ax_pi, ax_ptemp, ax_stemp, ax_ctemp,
                ax_sa, ax_uimu, ax_limu, ax_filt]

    for ax in all_axes:
        ax.set_facecolor('#1a1a1a')
        ax.tick_params(colors='#888888', labelsize=7)
        ax.xaxis.label.set_color('#888888')
        ax.yaxis.label.set_color('#888888')
        ax.title.set_color('#dddddd')
        for sp in ax.spines.values():
            sp.set_edgecolor('#2a2a2a')
        ax.grid(True, linestyle='--', alpha=0.2, color='#444444')

    # ── Row 0: Raw PPG ────────────────────────────────────────
    ax_ppg.set_title('Raw PPG — Dual Sensor', fontsize=9)
    ax_ppg.set_ylabel('Optical', fontsize=7)
    line_ira,  = ax_ppg.plot([], [], color='#4fa3f7', lw=0.8, label='IR avg')
    line_reda, = ax_ppg.plot([], [], color='#f76b6b', lw=0.8, label='Red avg')
    line_ir1,  = ax_ppg.plot([], [], color='#4fa3f7', lw=0.4, alpha=0.2, label='IR S1')
    line_ir2,  = ax_ppg.plot([], [], color='#a0d4ff', lw=0.4, alpha=0.2, label='IR S2')
    ax_ppg.legend(loc='upper right', facecolor='#1a1a1a', labelcolor='white', fontsize=7)

    # ── Row 1: Vitals ─────────────────────────────────────────
    ax_hr.set_title('Heart Rate', fontsize=9)
    ax_hr.set_ylabel('BPM', fontsize=7)
    ax_hr.set_ylim(30, 200)
    ax_hr.axhline(60,  color='#2ecc71', lw=0.4, alpha=0.4, ls='--')
    ax_hr.axhline(100, color='#f39c12', lw=0.4, alpha=0.4, ls='--')
    line_hr, = ax_hr.plot([], [], color='#e74c3c', lw=1.2)
    txt_hr   = ax_hr.text(0.05, 0.82, '--- BPM',
                           transform=ax_hr.transAxes,
                           fontsize=12, color='#e74c3c', fontweight='bold')

    ax_spo2.set_title('SpO2', fontsize=9)
    ax_spo2.set_ylabel('%', fontsize=7)
    ax_spo2.set_ylim(80, 102)
    ax_spo2.axhline(95,  color='#f39c12', lw=0.4, alpha=0.5, ls='--')
    ax_spo2.axhline(100, color='#e74c3c', lw=0.4, alpha=0.5, ls='--')
    line_spo2, = ax_spo2.plot([], [], color='#2ecc71', lw=1.2)
    txt_spo2   = ax_spo2.text(0.05, 0.82, '---%',
                               transform=ax_spo2.transAxes,
                               fontsize=12, color='#2ecc71', fontweight='bold')

    ax_br.set_title('Breathing Rate', fontsize=9)
    ax_br.set_ylabel('br/min', fontsize=7)
    ax_br.set_ylim(4, 40)
    ax_br.axhline(12, color='#2ecc71', lw=0.4, alpha=0.4, ls='--')
    ax_br.axhline(20, color='#f39c12', lw=0.4, alpha=0.4, ls='--')
    line_br, = ax_br.plot([], [], color='#9b59b6', lw=1.2)
    txt_br   = ax_br.text(0.05, 0.82, '---',
                           transform=ax_br.transAxes,
                           fontsize=12, color='#9b59b6', fontweight='bold')

    ax_hrv.set_title('HRV — RMSSD', fontsize=9)
    ax_hrv.set_ylabel('ms', fontsize=7)
    line_hrv, = ax_hrv.plot([], [], color='#f39c12', lw=1.2)
    txt_hrv   = ax_hrv.text(0.05, 0.82, '--- ms',
                             transform=ax_hrv.transAxes,
                             fontsize=12, color='#f39c12', fontweight='bold')

    # ── Row 2: Perfusion + Temperatures ──────────────────────
    ax_pi.set_title('Perfusion Index', fontsize=9)
    ax_pi.set_ylabel('PI %', fontsize=7)
    line_pi, = ax_pi.plot([], [], color='#1abc9c', lw=1.2)
    txt_pi   = ax_pi.text(0.05, 0.75, '--- %',
                           transform=ax_pi.transAxes,
                           fontsize=11, color='#1abc9c', fontweight='bold')
    txt_qual = ax_pi.text(0.05, 0.52, 'No contact',
                           transform=ax_pi.transAxes,
                           fontsize=8, color='#888888')

    ax_ptemp.set_title('PPG Onboard Temp', fontsize=9)
    ax_ptemp.set_ylabel('°C', fontsize=7)
    line_pt1, = ax_ptemp.plot([], [], color='#e67e22', lw=1.0, label='S1')
    line_pt2, = ax_ptemp.plot([], [], color='#e74c3c', lw=1.0, label='S2', ls='--')
    ax_ptemp.legend(loc='upper right', facecolor='#1a1a1a', labelcolor='white', fontsize=7)
    txt_ptemp = ax_ptemp.text(0.05, 0.82, '--°C',
                               transform=ax_ptemp.transAxes,
                               fontsize=11, color='#e67e22', fontweight='bold')

    ax_stemp.set_title('Skin Temp — Axilla', fontsize=9)
    ax_stemp.set_ylabel('°C', fontsize=7)
    line_tl, = ax_stemp.plot([], [], color='#3498db', lw=1.0, label='Left')
    line_tr, = ax_stemp.plot([], [], color='#e74c3c', lw=1.0, label='Right', ls='--')
    ax_stemp.legend(loc='upper right', facecolor='#1a1a1a', labelcolor='white', fontsize=7)
    txt_stemp = ax_stemp.text(0.05, 0.82, '--°C',
                               transform=ax_stemp.transAxes,
                               fontsize=11, color='#3498db', fontweight='bold')

    ax_ctemp.set_title('Skin Temp — Cervical C7', fontsize=9)
    ax_ctemp.set_ylabel('°C', fontsize=7)
    line_tc, = ax_ctemp.plot([], [], color='#2ecc71', lw=1.2)
    txt_ctemp = ax_ctemp.text(0.05, 0.82, '--°C',
                               transform=ax_ctemp.transAxes,
                               fontsize=11, color='#2ecc71', fontweight='bold')

    # ── Row 3: Spinal angle + IMU ─────────────────────────────
    ax_sa.set_title('Spinal Angle (Upper − Lower Pitch)', fontsize=9)
    ax_sa.set_ylabel('Degrees', fontsize=7)
    ax_sa.axhline(0,   color='#2ecc71', lw=0.6, alpha=0.5, ls='--')
    ax_sa.axhline(15,  color='#f39c12', lw=0.6, alpha=0.5, ls='--')
    ax_sa.axhline(-15, color='#f39c12', lw=0.6, alpha=0.5, ls='--')
    line_sa, = ax_sa.plot([], [], color='#4fa3f7', lw=1.2)
    txt_sa   = ax_sa.text(0.02, 0.82, 'SA: 0.0°',
                           transform=ax_sa.transAxes,
                           fontsize=12, color='#4fa3f7', fontweight='bold')
    txt_posture = ax_sa.text(0.35, 0.82, '',
                              transform=ax_sa.transAxes,
                              fontsize=12, fontweight='bold')

    ax_uimu.set_title('Upper IMU (C7) Pitch/Roll', fontsize=9)
    ax_uimu.set_ylabel('Degrees', fontsize=7)
    line_up, = ax_uimu.plot([], [], color='#9b59b6', lw=1.0, label='Pitch')
    line_ur, = ax_uimu.plot([], [], color='#e74c3c', lw=1.0, label='Roll', ls='--')
    ax_uimu.legend(loc='upper right', facecolor='#1a1a1a', labelcolor='white', fontsize=7)
    txt_uimu = ax_uimu.text(0.05, 0.82, 'P:0° R:0°',
                             transform=ax_uimu.transAxes,
                             fontsize=9, color='#9b59b6', fontweight='bold')

    ax_limu.set_title('Lower IMU (L4) Pitch/Roll', fontsize=9)
    ax_limu.set_ylabel('Degrees', fontsize=7)
    line_lp, = ax_limu.plot([], [], color='#1abc9c', lw=1.0, label='Pitch')
    line_lr, = ax_limu.plot([], [], color='#f39c12', lw=1.0, label='Roll', ls='--')
    ax_limu.legend(loc='upper right', facecolor='#1a1a1a', labelcolor='white', fontsize=7)
    txt_limu = ax_limu.text(0.05, 0.82, 'P:0° R:0°',
                             transform=ax_limu.transAxes,
                             fontsize=9, color='#1abc9c', fontweight='bold')

    # ── Row 4: Filtered PPG ───────────────────────────────────
    ax_filt.set_title('Filtered PPG — Bandpass 0.5–4Hz', fontsize=9)
    ax_filt.set_ylabel('Amplitude', fontsize=7)
    ax_filt.set_xlabel('Time (samples)', fontsize=7)
    line_filt,  = ax_filt.plot([], [], color='#2ecc71', lw=1.0)
    scat_peaks  = ax_filt.scatter([], [], color='#e74c3c', s=15, zorder=5,
                                   label='Beats')
    ax_filt.legend(loc='upper right', facecolor='#1a1a1a',
                   labelcolor='white', fontsize=7)

    # ==========================================================
    def safe_ylim(ax, vals, pad_frac=0.1, fallback=(0, 1)):
        valid = [v for v in vals if v != 0]
        if not valid:
            ax.set_ylim(*fallback)
            return
        mn, mx = min(valid), max(valid)
        pad = max((mx - mn) * pad_frac, 0.5)
        ax.set_ylim(mn - pad, mx + pad)

    def update(frame):
        with data_lock:
            x      = list(x_data)
            y_ir1  = list(ir1_data);   y_red1  = list(red1_data)
            y_ir2  = list(ir2_data)
            y_ira  = list(ira_data);   y_reda  = list(reda_data)
            y_pt1  = list(ppg_t1_data); y_pt2  = list(ppg_t2_data)
            y_tl   = list(tl_data);    y_tr    = list(tr_data)
            y_tc   = list(tc_data)
            y_up   = list(up_data);    y_ur    = list(ur_data)
            y_lp   = list(lp_data);    y_lr    = list(lr_data)
            y_sa   = list(sa_data);    y_pp    = list(pp_data)
            y_hr   = list(hr_data);    y_spo2  = list(spo2_data)
            y_br   = list(br_data);    y_hrv   = list(hrv_data)
            y_pi   = list(pi_data)

        xmin, xmax = min(x), max(x) + 1

        # Raw PPG
        line_ira.set_data(x, y_ira);    line_reda.set_data(x, y_reda)
        line_ir1.set_data(x, y_ir1);    line_ir2.set_data(x, y_ir2)
        ax_ppg.set_xlim(xmin, xmax)
        safe_ylim(ax_ppg, y_ira + y_reda, fallback=(0, 50000))

        # HR
        line_hr.set_data(x, y_hr)
        ax_hr.set_xlim(xmin, xmax)
        v = y_hr[-1]
        if v > 0:
            txt_hr.set_text(f'{v} BPM'); txt_hr.set_color(c_hr(v))

        # SpO2
        line_spo2.set_data(x, y_spo2)
        ax_spo2.set_xlim(xmin, xmax)
        v = y_spo2[-1]
        if v > 0:
            txt_spo2.set_text(f'{v}%'); txt_spo2.set_color(c_spo2(v))

        # BR
        line_br.set_data(x, y_br)
        ax_br.set_xlim(xmin, xmax)
        v = y_br[-1]
        if v > 0:
            txt_br.set_text(f'{v} br/min'); txt_br.set_color(c_br(v))

        # HRV
        line_hrv.set_data(x, y_hrv)
        ax_hrv.set_xlim(xmin, xmax)
        safe_ylim(ax_hrv, y_hrv, fallback=(0, 100))
        v = y_hrv[-1]
        if v > 0:
            txt_hrv.set_text(f'{v} ms')

        # PI
        line_pi.set_data(x, y_pi)
        ax_pi.set_xlim(xmin, xmax)
        safe_ylim(ax_pi, y_pi, fallback=(0, 5))
        v = y_pi[-1]
        txt_pi.set_text(f'{v}%')
        txt_qual.set_text(signal_quality(v))

        # PPG onboard temp
        line_pt1.set_data(x, y_pt1); line_pt2.set_data(x, y_pt2)
        ax_ptemp.set_xlim(xmin, xmax)
        safe_ylim(ax_ptemp, y_pt1 + y_pt2, pad_frac=0.05, fallback=(20, 45))
        v = y_pt1[-1]
        if v > 0:
            txt_ptemp.set_text(f'{v:.1f}°C'); txt_ptemp.set_color(c_temp(v))

        # Axilla skin temps
        line_tl.set_data(x, y_tl); line_tr.set_data(x, y_tr)
        ax_stemp.set_xlim(xmin, xmax)
        safe_ylim(ax_stemp, y_tl + y_tr, pad_frac=0.05, fallback=(30, 40))
        v = y_tl[-1]
        if v > 0:
            txt_stemp.set_text(f'L:{v:.1f}°'); txt_stemp.set_color(c_temp(v))

        # Cervical temp
        line_tc.set_data(x, y_tc)
        ax_ctemp.set_xlim(xmin, xmax)
        safe_ylim(ax_ctemp, y_tc, pad_frac=0.05, fallback=(30, 40))
        v = y_tc[-1]
        if v > 0:
            txt_ctemp.set_text(f'{v:.1f}°C'); txt_ctemp.set_color(c_temp(v))

        # Spinal angle
        line_sa.set_data(x, y_sa)
        ax_sa.set_xlim(xmin, xmax)
        safe_ylim(ax_sa, y_sa, pad_frac=0.2, fallback=(-30, 30))
        v_sa = y_sa[-1]
        txt_sa.set_text(f'SA: {v_sa:.1f}°')
        pl, pc = posture_label(v_sa)
        txt_posture.set_text(pl); txt_posture.set_color(pc)

        # Upper IMU
        line_up.set_data(x, y_up); line_ur.set_data(x, y_ur)
        ax_uimu.set_xlim(xmin, xmax)
        safe_ylim(ax_uimu, y_up + y_ur, pad_frac=0.2, fallback=(-90, 90))
        txt_uimu.set_text(f'P:{y_up[-1]:.1f}° R:{y_ur[-1]:.1f}°')

        # Lower IMU
        line_lp.set_data(x, y_lp); line_lr.set_data(x, y_lr)
        ax_limu.set_xlim(xmin, xmax)
        safe_ylim(ax_limu, y_lp + y_lr, pad_frac=0.2, fallback=(-90, 90))
        txt_limu.set_text(f'P:{y_lp[-1]:.1f}° R:{y_lr[-1]:.1f}°')

        # Filtered PPG with beat markers
        ir_arr = np.array(y_ira, dtype=float)
        if len(ir_arr) >= SAMPLE_RATE * 4 and np.std(ir_arr) > 0:
            filtered = bandpass_filter(ir_arr, 0.5, 4.0, SAMPLE_RATE)
            line_filt.set_data(x, filtered)
            ax_filt.set_xlim(xmin, xmax)
            mn, mx = filtered.min(), filtered.max()
            pad = max((mx - mn) * 0.1, 1)
            ax_filt.set_ylim(mn - pad, mx + pad)
            min_d = int(SAMPLE_RATE * 60 / 180)
            peaks, _ = find_peaks(-filtered, distance=min_d,
                                   prominence=np.std(filtered) * 0.5)
            if len(peaks) > 0:
                px = [x[i] for i in peaks if i < len(x)]
                py = [filtered[i] for i in peaks if i < len(filtered)]
                scat_peaks.set_offsets(np.c_[px, py])

        return (line_ira, line_reda, line_ir1, line_ir2,
                line_hr, line_spo2, line_br, line_hrv,
                line_pi, line_pt1, line_pt2,
                line_tl, line_tr, line_tc,
                line_sa, line_up, line_ur, line_lp, line_lr,
                line_filt,
                txt_hr, txt_spo2, txt_br, txt_hrv,
                txt_pi, txt_qual, txt_ptemp, txt_stemp,
                txt_ctemp, txt_sa, txt_posture,
                txt_uimu, txt_limu)

    ani = animation.FuncAnimation(
        fig, update, interval=100, blit=False, cache_frame_data=False
    )

    plt.suptitle('Aegis Vest — Full Telemetry Dashboard',
                 color='white', fontsize=13, y=0.99)
    plt.show()

if __name__ == "__main__":
    main()
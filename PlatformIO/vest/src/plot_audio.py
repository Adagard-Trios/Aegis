import serial
import time
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import collections

# --- CONFIGURATION ---
SERIAL_PORT = 'COM4'  # Update this to your active COM port
BAUD_RATE = 115200
X_LEN = 300           # Number of data points to display on screen

# --- DATA STORAGE ---
# Initialize deques with a default center value (2048)
data_ecg_i = collections.deque([2048.0] * X_LEN, maxlen=X_LEN)
data_ecg_ii = collections.deque([2048.0] * X_LEN, maxlen=X_LEN)
data_ecg_iii = collections.deque([2048.0] * X_LEN, maxlen=X_LEN)
data_ppg = collections.deque([2048.0] * X_LEN, maxlen=X_LEN)

# Variable for temperature
current_temp = "---"

# Setup Serial Connection
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2) # Wait for ESP32 to reboot
    print(f"Connected to {SERIAL_PORT}! Starting Aegis MedVerse Dashboard...")
except Exception as e:
    print(f"Error: Could not open serial port {SERIAL_PORT}. {e}")
    exit()

# --- PLOT SETUP ---
fig, (ax_ecg, ax_ppg) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
fig.canvas.manager.set_window_title('Aegis MedVerse - Real-Time Health Telemetry')
fig.patch.set_facecolor('#0F0F0F') # Dark theme

# ECG Plot Styles
ax_ecg.set_facecolor('black')
ax_ecg.set_title("ECG Waveforms (Leads I, II, III)", color='white', loc='left')
line_i, = ax_ecg.plot(data_ecg_i, label="Lead I", color='#FF3131', linewidth=1.5)
line_ii, = ax_ecg.plot(data_ecg_ii, label="Lead II", color='#318CE7', linewidth=1.5)
line_iii, = ax_ecg.plot(data_ecg_iii, label="Lead III", color='#00FF41', linewidth=2)
ax_ecg.legend(loc='upper right', fontsize='small', facecolor='black', labelcolor='white')
ax_ecg.grid(color='#333333', linestyle='--', linewidth=0.5)

# PPG Plot Styles
ax_ppg.set_facecolor('black')
ax_ppg.set_title("PPG - Pulse Plethysmograph", color='white', loc='left')
line_ppg, = ax_ppg.plot(data_ppg, label="Blood Volume Pulse", color='#FFFF00', linewidth=2)
ax_ppg.grid(color='#333333', linestyle='--', linewidth=0.5)

# On-Screen Text
temp_text = fig.text(0.75, 0.92, f'TEMP: {current_temp} °C', color='#FF9900', fontsize=16, fontweight='bold')
status_text = fig.text(0.1, 0.02, 'System Status: Receiving Data...', color='#00FF41', fontsize=10)

def update(frame):
    global current_temp
    
    # Read all available lines from Serial
    while ser.in_waiting:
        try:
            line = ser.readline().decode('utf-8').strip()
            # Look for our Teleplot tags ">Name:Value"
            if line.startswith('>'):
                parts = line[1:].split(':')
                if len(parts) == 2:
                    name, val = parts[0], float(parts[1])
                    
                    if name == "ECG_I": data_ecg_i.append(val)
                    elif name == "ECG_II": data_ecg_ii.append(val)
                    elif name == "ECG_III": data_ecg_iii.append(val)
                    elif name == "PPG_Wave": data_ppg.append(val)
                    elif name == "Temp":
                        current_temp = f"{val:.1f}"
                        temp_text.set_text(f'TEMP: {current_temp} °C')
        except:
            pass # Ignore corrupted lines

    # Update Waveforms
    line_i.set_ydata(data_ecg_i)
    line_ii.set_ydata(data_ecg_ii)
    line_iii.set_ydata(data_ecg_iii)
    line_ppg.set_ydata(data_ppg)

    # Dynamic Scaling for ECG
    ymin = min(min(data_ecg_i), min(data_ecg_ii), min(data_ecg_iii))
    ymax = max(max(data_ecg_i), max(data_ecg_ii), max(data_ecg_iii))
    ax_ecg.set_ylim(ymin - 200, ymax + 200)

    # Dynamic Scaling for PPG
    ax_ppg.set_ylim(min(data_ppg) - 100, max(data_ppg) + 100)

    return line_i, line_ii, line_iii, line_ppg, temp_text

# Run Animation
ani = FuncAnimation(fig, update, interval=20, blit=False, cache_frame_data=False)
plt.tight_layout(rect=[0, 0.05, 1, 0.95])
plt.show()

ser.close()
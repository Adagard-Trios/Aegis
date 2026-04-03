# Aegis Vest — Complete Hardware Wiring Guide
> ESP32-S3-DevKitC-1  ·  All wiring derived from `src/config.h`

---

## Quick Reference — All Pin Assignments

| GPIO | Function | Sensor | Signal |
|------|----------|--------|--------|
| **16** | SDA (I2C Bus 1) | MAX30102 #1 + HW-611 | Data |
| **21** | SCL (I2C Bus 1) | MAX30102 #1 + HW-611 | Clock |
| **4**  | SDA (I2C Bus 2) | MAX30102 #2 | Data |
| **5**  | SCL (I2C Bus 2) | MAX30102 #2 | Clock |
| **6**  | SDA (Software I2C) | GY-87 IMU | Data |
| **7**  | SCL (Software I2C) | GY-87 IMU | Clock |
| **15** | OneWire | DS18B20 ×3 | Data |
| **17** | Digital I/O | DHT11 | Data (single-wire) |
| **8**  | Analog In (ADC) | AD8232 | Lead I (OUT pin) |
| **9**  | Analog In (ADC) | AD8232 | Lead II (OUT pin) |
| **14** | Analog In (ADC) | MAX9814 | Audio OUT |
| **42** | I2S BCLK | INMP441 | Bit clock |
| **45** | I2S WS / LRCK | INMP441 | Word select |
| **48** | I2S SD | INMP441 | Serial data |
| **3.3V** | Power | All sensors | VCC |
| **GND** | Ground | All sensors | GND |

> ⚠️ **All sensors use 3.3 V — never connect to 5 V rail.**

---

## 1 · MAX30102 Pulse Oximeter / PPG — Sensor 1

**I2C Bus 1 · Fixed address 0x57**

| MAX30102 Pin | ESP32-S3 GPIO | Notes |
|--------------|--------------|-------|
| VIN / VCC | 3.3 V | |
| GND | GND | |
| SDA | **GPIO 16** | Needs 4.7 kΩ pull-up → 3.3 V ✱ |
| SCL | **GPIO 21** | Needs 4.7 kΩ pull-up → 3.3 V ✱ |
| INT | Not connected | Optional interrupt, unused in code |

✱ **Mandatory pull-up resistors:** Connect one 4.7 kΩ resistor from GPIO 16 → 3.3 V and one from GPIO 21 → 3.3 V.  
Most MAX30102 breakout boards already have these on-board — check for `R1`/`R2` on the PCB.

```
ESP32-S3                 MAX30102 #1
─────────────────────────────────────
3.3V ──────────────────── VIN
GND  ──────────────────── GND
GPIO 16 ──[4.7kΩ→3.3V]── SDA
GPIO 21 ──[4.7kΩ→3.3V]── SCL
```

---

## 2 · MAX30102 Pulse Oximeter / PPG — Sensor 2

**I2C Bus 2 · Fixed address 0x57**

| MAX30102 Pin | ESP32-S3 GPIO | Notes |
|--------------|--------------|-------|
| VIN / VCC | 3.3 V | |
| GND | GND | |
| SDA | **GPIO 4** | Needs 4.7 kΩ pull-up → 3.3 V ✱ |
| SCL | **GPIO 5** | Needs 4.7 kΩ pull-up → 3.3 V ✱ |
| INT | Not connected | |

> ⚠️ GPIO 4 and GPIO 5 are on a **separate I2C bus from Sensor 1**.  
> Both sensors share the same I2C address (0x57) — they **must** be on separate buses. This is already handled in the code.

```
ESP32-S3                 MAX30102 #2
─────────────────────────────────────
3.3V ──────────────────── VIN
GND  ──────────────────── GND
GPIO 4 ───[4.7kΩ→3.3V]── SDA
GPIO 5 ───[4.7kΩ→3.3V]── SCL
```

---

## 3 · DS18B20 Temperature Sensors (×3)

**OneWire bus · GPIO 15**  
All three sensors share the **same three wires** in a daisy-chain.

| DS18B20 Pin | ESP32-S3 GPIO | Notes |
|-------------|--------------|-------|
| VDD (red) | 3.3 V | |
| GND (black) | GND | |
| DATA (yellow/white) | **GPIO 15** | Needs 4.7 kΩ pull-up → 3.3 V |

```
ESP32-S3              DS18B20 #1      DS18B20 #2      DS18B20 #3
──────────────────────────────────────────────────────────────────
3.3V ─────┬────────── VDD  ─────────  VDD  ─────────  VDD
          │
         [4.7kΩ]
          │
GPIO 15 ──┴────────── DATA ─────────  DATA ─────────  DATA
GND  ─────────────── GND  ─────────  GND  ─────────  GND
```

**Sensor placement on vest:**
- Sensor 0 (index 0 in code) → Left axilla
- Sensor 1 (index 1) → Right axilla  
- Sensor 2 (index 2) → Cervical (back of neck)

> After first flash, open Serial Monitor and note each sensor's 8-byte address. Update `config.h` once you physically label which sensor is where.

---

## 4 · AD8232 ECG Module

The code reads **two analog output channels** to derive Leads I, II, and III (via Einthoven's law: Lead III = Lead II − Lead I).

| AD8232 Pin | ESP32-S3 GPIO | Notes |
|------------|--------------|-------|
| VCC | 3.3 V | |
| GND | GND | |
| OUTPUT (Lead I) | **GPIO 8** | Analog input |
| OUTPUT (Lead II) | **GPIO 9** | Analog input (second AD8232 module) |
| LO+ | Not used in code | Optional lead-off detection |
| LO− | Not used in code | Optional lead-off detection |
| SDN | GND | Tie LOW to keep the chip on |

> ⚠️ **Two AD8232 modules required** — one per output channel (Lead I and Lead II).  
> Alternatively, if your AD8232 module has two dedicated output pins, wire them to GPIO 8 and GPIO 9 respectively.

**Electrode placement (standard 3-lead ECG):**
```
       RA (Right Arm)  ──── AD8232 #1 electrode 1
       LA (Left Arm)   ──── AD8232 #1 electrode 2  →  GPIO 8 (Lead I)
       LL (Left Leg)   ──── AD8232 #2 electrode    →  GPIO 9 (Lead II)
```

```
ESP32-S3              AD8232 #1          AD8232 #2
────────────────────────────────────────────────────
3.3V ──────────────── VCC                VCC
GND  ──────────────── GND ────────────── GND
GPIO 8 ─────────────── OUTPUT (Lead I)
GPIO 9 ──────────────────────────────── OUTPUT (Lead II)
```

> ⏱ **90-second warmup:** The code ignores ECG readings for the first 90 seconds to allow dry electrodes to stabilise. Apply electrode gel or wet the pads for faster lock-on.

---

## 5 · MAX9814 Analog Microphone

| MAX9814 Pin | ESP32-S3 GPIO | Notes |
|-------------|--------------|-------|
| VDD | 3.3 V | |
| GND | GND | |
| OUT | **GPIO 14** | Analog output (ADC1 CH3) |
| GAIN | GND | Sets max gain (60 dB) — float for 50 dB, VDD for 40 dB |
| AR | Not connected | Auto-gain attack/release — leave floating |

```
ESP32-S3             MAX9814
──────────────────────────────
3.3V ──────────────── VDD
GND  ──────────────── GND
GPIO 14 ─────────────── OUT
GND  ──────────────── GAIN   (max gain)
```

---

## 6 · INMP441 I2S Digital Microphone

| INMP441 Pin | ESP32-S3 GPIO | Notes |
|-------------|--------------|-------|
| VDD | 3.3 V | |
| GND | GND | |
| SCK / BCLK | **GPIO 42** | Bit clock |
| WS / LRCK | **GPIO 45** | Word select (L/R channel) |
| SD / DATA | **GPIO 48** | Serial data out |
| L/R | GND | Tie to GND to select LEFT channel (matches `I2S_CHANNEL_FMT_ONLY_LEFT`) |

```
ESP32-S3             INMP441
──────────────────────────────
3.3V ──────────────── VDD
GND  ──────────────── GND
GPIO 42 ─────────────── SCK (BCLK)
GPIO 45 ─────────────── WS  (LRCK)
GPIO 48 ─────────────── SD  (DATA)
GND  ──────────────── L/R   ← MUST tie LOW for left-channel mode
```

> ⚠️ **L/R pin is mandatory.** If left floating the mic may produce silence or garbage data.

---

## 7 · GY-87 IMU (MPU6050 + HMC5883L + BMP180)

> **✅ STATUS: ACTIVE — Software I2C driver on GPIO 6/7.**  
> The firmware uses bit-banged I2C on GPIO 6 and 7, leaving both hardware I2C buses free for the MAX30102 sensors. MPU6050 (accel/gyro) and BMP180 (pressure/temp) are both read.

| GY-87 Pin | ESP32-S3 GPIO | Notes |
|-----------|--------------|-------|
| VCC | 3.3 V | |
| GND | GND | |
| SDA | **GPIO 6** | 4.7 kΩ pull-up → 3.3 V (most GY-87 boards have on-board pull-ups) |
| SCL | **GPIO 7** | 4.7 kΩ pull-up → 3.3 V (most GY-87 boards have on-board pull-ups) |
| INT | Not connected | Optional |

> GPIO 6 and GPIO 7 are general-purpose I/O on the ESP32-S3-DevKitC-1 (quad-SPI flash variant).  
> They are **not strapping pins** and are safe to use.  
> Since the firmware uses **software I2C** (bit-bang), these pins do NOT consume a hardware I2C peripheral.

```
ESP32-S3                GY-87
────────────────────────────────
3.3V ──┬─────────────── VCC
       ├──[4.7kΩ]── GPIO 6 ── SDA
       └──[4.7kΩ]── GPIO 7 ── SCL
GND  ──────────────── GND
```

> 💡 **Why software I2C?** The ESP32-S3 only has 2 hardware I2C peripherals. Both are used by the MAX30102 sensors (Bus 1 on GPIO 16/21 and Bus 2 on GPIO 4/5). Software I2C on GPIO 6/7 avoids any bus conflicts.

---

## 8 · HW-611 Barometric Pressure Sensor (BMP280)

**Shares I2C Bus 1 with MAX30102 #1 · Address 0x76**

| HW-611 Pin | ESP32-S3 / Connection | Notes |
|------------|----------------------|-------|
| VCC | 3.3 V | Some HW-611 modules have an onboard regulator — check yours; 3.3 V is safest |
| GND | GND | |
| SDA | **GPIO 16** | Shares Bus 1 with MAX30102 #1 — existing 4.7 kΩ pull-up covers this |
| SCL | **GPIO 21** | Shares Bus 1 with MAX30102 #1 — existing 4.7 kΩ pull-up covers this |
| SDO | **GND** | **MUST** tie to GND — sets I2C address to **0x76** |
| CSB | **3.3 V** | Tie HIGH to select I2C mode (not SPI) |

> The HW-611 (BMP280) at address 0x76 shares the bus with MAX30102 at 0x57 — no address conflict.  
> No additional pull-up resistors needed; the ones already on Bus 1 serve both sensors.

```
ESP32-S3                HW-611 (BMP280)
────────────────────────────────────────────
3.3V ──────────────────── VCC
GND  ──────────────────── GND
GPIO 16 ──[existing 4.7kΩ]── SDA   (shared with MAX30102 #1)
GPIO 21 ──[existing 4.7kΩ]── SCL   (shared with MAX30102 #1)
GND  ──────────────────── SDO   ← Forces address 0x76
3.3V ──────────────────── CSB   ← Selects I2C mode
```

> ⚠️ **SDO and CSB are critical.** If SDO is left floating, the address may be 0x77 (conflicting with GY-87's BMP180). If CSB is floating, the chip may enter SPI mode.

---

## 9 · DHT11 Temperature & Humidity Sensor

**Single-wire digital protocol · GPIO 17**

| DHT11 Pin | ESP32-S3 GPIO | Notes |
|-----------|--------------|-------|
| VCC / Pin 1 | 3.3 V | DHT11 operates from 3.0 to 5.5 V |
| DATA / Pin 2 | **GPIO 17** | **10 kΩ pull-up resistor required → 3.3 V** |
| NC / Pin 3 | — | Not connected |
| GND / Pin 4 | GND | |

> GPIO 17 is a general-purpose I/O on the ESP32-S3. Not a strapping pin, not used by flash/PSRAM.

```
ESP32-S3              DHT11
──────────────────────────────
3.3V ──┬────────────── VCC (Pin 1)
       │
      [10kΩ]
       │
GPIO 17─┴────────────── DATA (Pin 2)
GND  ──────────────── GND  (Pin 4)
```

> ⚠️ **The 10 kΩ pull-up is mandatory.** Without it, the DHT11 data line won't return HIGH between bits and all reads will fail.  
> Some DHT11 breakout boards (3-pin modules) include the pull-up on-board — check before adding an external one.

---

## Pull-Up Resistor Summary

| Bus | SDA Pin | SCL Pin | Resistor value | Connected to |
|-----|---------|---------|----------------|--------------|
| I2C Bus 1 (MAX30102 #1 + HW-611) | GPIO 16 | GPIO 21 | **4.7 kΩ each** | 3.3 V |
| I2C Bus 2 (MAX30102 #2) | GPIO 4 | GPIO 5 | **4.7 kΩ each** | 3.3 V |
| Software I2C (GY-87 IMU) | GPIO 6 | GPIO 7 | **4.7 kΩ each** | 3.3 V |
| OneWire (DS18B20) | GPIO 15 | — | **4.7 kΩ** | 3.3 V |
| DHT11 data | GPIO 17 | — | **10 kΩ** | 3.3 V |

> **Missing pull-ups are the #1 cause of I2C Error 263.**  
> If your breakout board does not include them, add them externally.

---

## Power Distribution

```
USB (5V)
   │
  [ ESP32-S3 on-board LDO ]
   │
  3.3V rail ─── MAX30102 #1 VIN
              ── MAX30102 #2 VIN
              ── HW-611       VCC (+ CSB)
              ── DHT11         VCC
              ── DS18B20 ×3  VDD
              ── AD8232 ×2   VCC
              ── MAX9814      VDD
              ── INMP441      VDD
              ── GY-87        VCC (3.3V)
```

> All sensors must share a **common GND** with the ESP32-S3.

---

## Checklist Before Flashing

- [ ] All sensor VCC/VIN pins connected to **3.3 V** (not 5 V)
- [ ] All sensor GND pins connected to **ESP32-S3 GND**
- [ ] 4.7 kΩ pull-ups on every I2C SDA and SCL line
- [ ] 4.7 kΩ pull-up on DS18B20 data line (GPIO 15)
- [ ] INMP441 **L/R pin tied to GND**
- [ ] AD8232 **SDN pin tied to GND**
- [ ] MAX9814 **GAIN pin tied to GND** (or left floating for 50 dB)
- [ ] No GPIO 19 or 20 used (these are USB D−/D+ on ESP32-S3)
- [ ] GY-87 connected to GPIO 6 (SDA) and GPIO 7 (SCL)
- [ ] HW-611 **SDO pin tied to GND** (sets address 0x76)
- [ ] HW-611 **CSB pin tied to 3.3 V** (selects I2C mode)
- [ ] HW-611 SDA/SCL on GPIO 16/21 (shared with MAX30102 #1)
- [ ] DHT11 data on GPIO 17 with **10 kΩ pull-up to 3.3 V**

---

## Expected Serial Output After Correct Wiring

```
[SENSOR] Buses initialized.
[SCAN] Bus 1 (GPIO 16/21):
  Found: 0x57
  Found: 0x76
[SCAN] Bus 2 (GPIO 4/5):
  Found: 0x57
[SENSOR] Sensor 1 OK.
[SENSOR] Sensor 2 OK.
[SENSOR] MODE: DUAL
[TEMP] Found 3 DS18B20 sensor(s).
[ECG] Initialized on GPIO 8/9.
[AUDIO] MAX9814 analog mic on GPIO 14.
[AUDIO] INMP441 I2S mic OK.
[IMU] Initializing GY-87 on software I2C...
[IMU] SDA=GPIO 6, SCL=GPIO 7
[IMU] Scanning software I2C bus...
[IMU]   Found device at 0x68
[IMU]   Found device at 0x77
[IMU] MPU6050 OK (WHO_AM_I 0x68).
[IMU] BMP180 OK — calibration loaded.
[IMU] GY-87 ready.
[ENV] Initializing environment sensors...
[ENV] BMP280 OK on Bus 1 (chip 0x58, addr 0x76).
[ENV] DHT11 OK on GPIO 17 (25.0°C, 55% RH).
[ENV] Environment sensors ready.
[MAIN] All systems initialised.
```

If you see `Found: 0x57` and `Found: 0x76` on Bus 1, both MAX30102 #1 and HW-611 are wired correctly.

---

---

# Hardware Fix Guide — I2C Error 263

> **Error 263 = `ESP_ERR_TIMEOUT`** — the ESP32-S3 sent a message on the I2C bus and nothing replied.  
> This section walks through every possible cause and exactly how to fix it with the components you already have.

---

## Step 1 — Isolate which sensor is failing

Flash the firmware and open the Serial Monitor at 115200 baud.  
Look at the startup scan output:

```
[SCAN] Bus 1 (GPIO 16/21):
  NOTHING FOUND          ← Sensor 1 is the problem
[SCAN] Bus 2 (GPIO 4/5):
  Found: 0x57            ← Sensor 2 is fine
```

This tells you exactly which I2C bus and which physical sensor to debug.  
Fix one bus at a time — do not move on until `Found: 0x57` appears for that bus.

---

## Step 2 — Check power with a multimeter

Set your multimeter to **DC Voltage** mode.

| Test point | Expected reading | If wrong |
|------------|-----------------|----------|
| ESP32-S3 3V3 pin → GND | **3.28 – 3.35 V** | USB cable issue or board fault |
| MAX30102 VIN pin → GND | **3.28 – 3.35 V** | Broken wire or bad solder joint on VIN |
| MAX30102 GND pin → ESP GND | **0 V** | Open ground — re-solder GND connection |

> If VIN is correct but the sensor still doesn't respond, the problem is the I2C lines — move to Step 3.

---

## Step 3 — Check SDA/SCL voltage (idle state)

With the **ESP32-S3 powered on** and firmware running, measure:

| Pin | Expected voltage (idle) | What it means if wrong |
|-----|------------------------|------------------------|
| SDA (GPIO 16 or 4) | **2.8 – 3.3 V** | Pulled HIGH by pull-up resistor |
| SCL (GPIO 21 or 5) | **2.8 – 3.3 V** | Pulled HIGH by pull-up resistor |

### If SDA or SCL reads 0 V (LOW):
The line is being pulled to ground — either:
- **No pull-up resistor** is present → Go to Step 4
- A **short circuit** exists between SDA/SCL and GND → Go to Step 6

### If SDA or SCL reads ~1.6 V (mid-rail):
Two pull-up resistors are fighting each other (both sensors sharing one bus incorrectly). Check you have the sensors on **separate buses** (Sensor 1 on GPIO 16/21, Sensor 2 on GPIO 4/5).

### If SDA/SCL reads 3.3 V but sensor still not found:
Pull-ups are fine — the sensor itself is the issue → Go to Step 7.

---

## Step 4 — Adding pull-up resistors from your components kit

This is the **most common fix**. I2C lines must be pulled HIGH to 3.3 V.

### What resistor value to use

| You have | Works? | Notes |
|----------|--------|-------|
| 4.7 kΩ | ✅ Best | Ideal value |
| 3.3 kΩ | ✅ Fine | Slightly stronger pull — works well up to 1 m wire |
| 2.2 kΩ | ✅ Fine | Good for noisy environments |
| 10 kΩ | ⚠️ Marginal | Will work on a breadboard with short wires |
| Two 10 kΩ in parallel | ✅ Fine | Gives 5 kΩ — effectively same as 4.7 kΩ |
| 1 kΩ | ❌ Too strong | May violate I2C spec and damage GPIO |
| 100 kΩ | ❌ Too weak | Won't pull up reliably |

### How to add pull-ups — step by step

For **each** I2C bus that is failing:

```
You need: 2 resistors (SDA + SCL) per bus
          That's 4 resistors total for both MAX30102 buses
```

**On a breadboard:**
1. Connect a wire from the ESP32-S3 **3.3V pin** to a free row on the breadboard
2. Insert the resistor between that 3.3V row and the row where your SDA wire lands
3. Repeat for SCL

```
Breadboard rows:
  [A] — 3.3V rail
  [B] — empty (resistor leg 1 here)
  [C] — SDA wire from ESP32 + SDA wire to sensor (resistor leg 2 here)

  Insert resistor between [B] and [C], then bridge [A] to [B] with a short wire.
```

**On perfboard / flying leads (no breadboard):**
1. Take a 4.7 kΩ resistor
2. Connect one leg to the 3.3V wire of the sensor (already going to VIN)
3. Connect the other leg to the SDA wire
4. Repeat for SCL

```
Physical connection:

  3.3V ────┬────── MAX30102 VIN
           │
          [4.7kΩ]
           │
  GPIO 16 ─┴────── MAX30102 SDA
```

> **Tip:** Twist the resistor leads around the wire junction and tape with electrical tape if you don't have solder available.

---

## Step 5 — Check if your MAX30102 breakout already has pull-ups

Many MAX30102 breakout boards include **on-board pull-up resistors**. If yours does, you **do not need to add them**.

### How to check without a datasheet

1. Look at the back of the PCB for small SMD components (tiny black rectangles) near the SDA and SCL pads
2. Use your multimeter in **resistance mode** (Ω):
   - Power OFF the board
   - Measure resistance between SDA and 3.3V (VIN) pad
   - Measure resistance between SCL and 3.3V (VIN) pad

| Reading | Meaning |
|---------|---------|
| 4 kΩ – 10 kΩ | ✅ Pull-ups already present — do NOT add more |
| > 100 kΩ or OL (open) | ❌ No pull-ups — you must add them externally |

> ⚠️ If pull-ups are already on the board AND you add external ones, you get two resistors in parallel making the pull too strong. This can cause communication errors on its own. **Measure first, then decide.**

---

## Step 6 — Check for short circuits

If SDA or SCL reads **0 V** with power on, suspect a short to GND.

**Test with multimeter in continuity mode (beep mode):**
- Power **OFF** the ESP32
- Probe between **SDA and GND**
- Probe between **SCL and GND**

| Result | Meaning |
|--------|---------|
| Beep / < 10 Ω | ❌ Short circuit — find and fix the bridge |
| No beep / > 1 MΩ | ✅ No short — problem is elsewhere |

**Common causes of shorts:**
- Solder bridge between adjacent pads on the sensor breakout
- Breadboard row accidentally shared between SDA and GND
- Dupont wire insulation stripped too far — bare conductor touching GND pin

**Fix:** Use a magnifying glass and look at each solder joint. Reflow suspicious joints. On a breadboard, re-seat all wires and ensure they are in the correct rows.

---

## Step 7 — Sensor not responding despite correct wiring

If power is good, pull-ups are present, SDA/SCL idle at 3.3 V, but the scan still shows `NOTHING FOUND`:

### Test A — Swap the sensor

If you have a second MAX30102, swap it in place of the suspect one.  
If the new one shows `Found: 0x57` → the original sensor is faulty (dead chip or delaminated solder ball). Replace it.

### Test B — Shorten the wires

I2C is sensitive to wire capacitance. Long wires (> 30 cm) cause the signal edges to soften and trigger timeouts.

- Replace any wire longer than 20 cm with a shorter one
- Twist SDA and SCL wires together to reduce pickup noise

### Test C — Check solder joints under load

Gently press down on the sensor breakout board while watching the Serial Monitor.  
If the device suddenly appears → you have a **cold solder joint** (intermittent contact).  
Re-solder all pins on the breakout board.

### Test D — Lower the I2C clock speed

The code initialises at 100 kHz (standard mode), which is already conservative.  
If nothing else works, try dropping to 50 kHz temporarily to rule out timing issues:

In `sensor_manager.cpp`, change:
```cpp
// Current
_bus1.begin(SDA1, SCL1, 100000);

// Test at half speed
_bus1.begin(SDA1, SCL1, 50000);
```

---

## Step 8 — Run the I2C scanner to confirm fix

Before flashing the full firmware, you can upload this standalone I2C scanner to the ESP32-S3 to check each bus independently. Paste into a fresh `main.cpp`:

```cpp
#include <Arduino.h>
#include <Wire.h>

TwoWire bus1(0);  // Bus 1: SDA=16, SCL=21
TwoWire bus2(1);  // Bus 2: SDA=4,  SCL=5

void scanBus(TwoWire &bus, const char* label) {
  Serial.printf("\n=== %s ===\n", label);
  bool found = false;
  for (byte addr = 1; addr < 127; addr++) {
    bus.beginTransmission(addr);
    if (bus.endTransmission() == 0) {
      Serial.printf("  Device found at 0x%02X\n", addr);
      found = true;
    }
  }
  if (!found) Serial.println("  NOTHING FOUND");
}

void setup() {
  Serial.begin(115200);
  delay(2000);
  bus1.begin(16, 21, 100000);
  bus2.begin(4,  5,  100000);
  bus1.setTimeOut(50);
  bus2.setTimeOut(50);
  scanBus(bus1, "Bus 1 — GPIO 16 (SDA) / 21 (SCL)");
  scanBus(bus2, "Bus 2 — GPIO 4  (SDA) / 5  (SCL)");
}

void loop() {
  delay(3000);
  scanBus(bus1, "Bus 1");
  scanBus(bus2, "Bus 2");
}
```

**Expected output (when wired correctly):**
```
=== Bus 1 — GPIO 16 (SDA) / 21 (SCL) ===
  Device found at 0x57

=== Bus 2 — GPIO 4  (SDA) / 5  (SCL) ===
  Device found at 0x57
```

Once both show `0x57`, flash the full vest firmware — Error 263 will be gone.

---

## Summary — Error 263 Diagnosis Flowchart

```
Error 263 appearing?
        │
        ▼
  Check Serial scan output
        │
  ┌─────┴──────┐
  │            │
NOTHING     Found:0x57
FOUND       but errors
  │         later → Step 7
  ▼
Measure SDA/SCL idle voltage
        │
  ┌─────┴──────────────┐
  │                    │
0 V (pulled LOW)    3.3 V (correct)
  │                    │
  ▼                    ▼
Check for         But scan still fails?
short circuit     → Check power (Step 2)
(Step 6)          → Swap sensor (Step 7)
  │
No short found?
  │
  ▼
Add 4.7 kΩ pull-up resistors
SDA → 3.3V and SCL → 3.3V
(Step 4)
  │
  ▼
Re-scan → Found: 0x57 ✅
```

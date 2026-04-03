#include <Arduino.h>

// PIN DEFINITIONS
#define SENSOR_A_OUT 1   // Lead I
#define SENSOR_B_OUT 2   // Lead II

#define SENSOR_A_LO_POS 4
#define SENSOR_A_LO_NEG 5
#define SENSOR_B_LO_POS 6
#define SENSOR_B_LO_NEG 7

// FILTER CONSTANTS
float filteredI = 2048.0;
float filteredII = 2048.0;
const float alpha = 0.3; // Smoothing factor (0.1 to 0.4)

// 50Hz Notch Filter Variables (for 200Hz sampling)
float xI_1=0, xI_2=0, yI_1=0, yI_2=0;
float xII_1=0, xII_2=0, yII_1=0, yII_2=0;

// Notch coefficients for 50Hz @ 200Hz Sample Rate
const float b0 = 0.965, b1 = -0.0, b2 = 0.965;
const float a1 = -0.0, a2 = 0.931;

float applyNotch(float input, float &x1, float &x2, float &y1, float &y2) {
    float output = b0*input + b1*x1 + b2*x2 - a1*y1 - a2*y2;
    x2 = x1; x1 = input;
    y2 = y1; y1 = output;
    return output;
}

void setup() {
    // High speed for Python plotter
    Serial.begin(921600); 
    
    // Setup Leads-Off Detection pins - Ensure these aren't tied to 3.3V/GND anymore!
    pinMode(SENSOR_A_LO_POS, INPUT);
    pinMode(SENSOR_A_LO_NEG, INPUT);
    pinMode(SENSOR_B_LO_POS, INPUT);
    pinMode(SENSOR_B_LO_NEG, INPUT);

    // ESP32-S3 high-resolution ADC
    analogReadResolution(12); // 0 - 4095
}

void loop() {
    // 1. Check if pads are disconnected
    bool leadsOff = digitalRead(SENSOR_A_LO_POS) || digitalRead(SENSOR_A_LO_NEG) || 
                    digitalRead(SENSOR_B_LO_POS) || digitalRead(SENSOR_B_LO_NEG);

    if (leadsOff) {
        // Keeps the graph from jumping wildly when leads are off
        Serial.println("Lead_I:2048,Lead_II:2048,Lead_III:2048");
    } else {
        // 2. Read Raw Data
        int rawA = analogRead(SENSOR_A_OUT);
        int rawB = analogRead(SENSOR_B_OUT);

        // 3. Apply 50Hz Notch Filter (Removes electrical hum from laptop charger)
        float notchI = applyNotch((float)rawA, xI_1, xI_2, yI_1, yI_2);
        float notchII = applyNotch((float)rawB, xII_1, xII_2, yII_1, yII_2);

        // 4. Exponential Moving Average (Smooths out fine-grain jitter)
        filteredI = (alpha * notchI) + ((1.0 - alpha) * filteredI);
        filteredII = (alpha * notchII) + ((1.0 - alpha) * filteredII);

        // 5. EINTHOVEN'S LAW: Lead III = Lead II - Lead I
        // Offset by 2048 to keep the signal visible in the middle of the graph
        int derivedIII = (int)(filteredII - filteredI) + 2048;

        // 6. Output formatted for your Python script
        Serial.print("Lead_I:");   Serial.print((int)filteredI);  Serial.print(",");
        Serial.print("Lead_II:");  Serial.print((int)filteredII); Serial.print(",");
        Serial.print("Lead_III:"); Serial.println(derivedIII);
    }

    // 200Hz Sample rate for clear P-QRS-T complexes
    delay(5); 
}
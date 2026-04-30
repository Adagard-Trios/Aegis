"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { buildStreamUrl } from "../lib/api";

export interface TelemetryData {
  timestamp: number;
  ppg: {
    ir1: number;
    red1: number;
    ir2: number;
    red2: number;
    ira: number;
    reda: number;
    t1: number;
    t2: number;
  };
  temperature: {
    left_axilla: number;
    right_axilla: number;
    cervical: number;
  };
  imu: {
    upper_pitch: number;
    upper_roll: number;
    lower_pitch: number;
    lower_roll: number;
    spinal_angle: number;
    poor_posture: boolean;
    posture_label: string;
    bmp180_pressure?: number;
    bmp180_temp?: number;
  };
  environment?: {
    bmp280_pressure: number;
    bmp280_temp: number;
    dht11_humidity: number;
    dht11_temp: number;
  };
  ecg: {
    lead1: number;
    lead2: number;
    lead3: number;
    ecg_hr: number;
  };
  audio: {
    analog_rms: number;
    digital_rms: number;
  };
  vitals: {
    heart_rate: number;
    spo2: number;
    breathing_rate: number;
    hrv_rmssd: number;
    perfusion_index: number;
    signal_quality: string;
  };
  connection: {
    vest_connected: boolean;
    fetal_connected: boolean;
    using_mock: boolean;
  };
  fetal?: {
    mode: number;
    piezo_raw: number[];
    kicks: boolean[];
    movement: boolean[];
    mic_volts: number[];
    heart_tones: boolean[];
    bowel_sounds: boolean[];
    film_pressure: number[];
    contractions: boolean[];
  };
  pharmacology?: {
    active_medication: string | null;
    dose: number;
    sim_time: number;
    clearance_model: string;
    effect_curve?: number;
    k_el?: number;
  };
  imu_derived?: {
    tremor: { band_power: number; total_power: number; band_ratio: number; tremor_flag: boolean };
    gait: { stride_count: number; mean_stride_s: number; stride_cv: number; asymmetry_flag: boolean };
    pots: { hr_jump: number; angle_delta: number; pots_flag: boolean };
    activity_state: "rest" | "walking" | "running" | "unknown";
  };
  waveform?: {
    fs: number;
    ecg_lead1: number[];
    ecg_lead2: number[];
    ecg_lead3: number[];
    ppg_ira: number[];
    ppg_reda: number[];
    audio: number[];
  } | null;
}

export function useVestStream() {
  const [data, setData] = useState<TelemetryData | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    try {
      const es = new EventSource(buildStreamUrl("/stream"));
      eventSourceRef.current = es;

      es.onopen = () => {
        setConnected(true);
        setError(null);
      };

      es.onmessage = (event) => {
        try {
          const parsed: TelemetryData = JSON.parse(event.data);
          setData(parsed);
        } catch {
          // skip malformed messages
        }
      };

      es.onerror = () => {
        setConnected(false);
        setError("Connection lost — reconnecting...");
        es.close();
        // Reconnect after 3 seconds
        reconnectTimeoutRef.current = setTimeout(connect, 3000);
      };
    } catch {
      setError("Failed to connect to telemetry stream");
      reconnectTimeoutRef.current = setTimeout(connect, 3000);
    }
  }, []);

  useEffect(() => {
    connect();

    return () => {
      eventSourceRef.current?.close();
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [connect]);

  return { data, connected, error };
}

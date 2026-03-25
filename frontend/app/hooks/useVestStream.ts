"use client";

import { useState, useEffect, useRef, useCallback } from "react";

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
    using_mock: boolean;
  };
}

const STREAM_URL = "http://localhost:8000/stream";

export function useVestStream() {
  const [data, setData] = useState<TelemetryData | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    try {
      const es = new EventSource(STREAM_URL);
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

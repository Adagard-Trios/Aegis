#include "audio_manager.h"

AudioManager::AudioManager() {}

bool AudioManager::begin() {
  pinMode(MIC_ANALOG_PIN, INPUT);
  Serial.println("[AUDIO] MAX9814 analog mic on GPIO 14.");

  i2s_config_t cfg = {
    .mode                 = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
    .sample_rate          = 16000,
    .bits_per_sample      = I2S_BITS_PER_SAMPLE_32BIT,
    .channel_format       = I2S_CHANNEL_FMT_ONLY_LEFT,
    .communication_format = I2S_COMM_FORMAT_STAND_I2S,
    .intr_alloc_flags     = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count        = 4,
    .dma_buf_len          = 256,
    .use_apll             = false,
    .tx_desc_auto_clear   = false,
    .fixed_mclk           = 0
  };

  i2s_pin_config_t pins = {
    .bck_io_num   = I2S_SCK_PIN,
    .ws_io_num    = I2S_WS_PIN,
    .data_out_num = I2S_PIN_NO_CHANGE,
    .data_in_num  = I2S_SD_PIN
  };

  if (i2s_driver_install(I2S_NUM_0, &cfg, 0, NULL) != ESP_OK) {
    Serial.println("[AUDIO] INMP441 driver install FAILED.");
    return false;
  }
  if (i2s_set_pin(I2S_NUM_0, &pins) != ESP_OK) {
    Serial.println("[AUDIO] INMP441 pin config FAILED.");
    return false;
  }

  _i2sOk = true;
  Serial.println("[AUDIO] INMP441 I2S mic OK.");
  return true;
}

void AudioManager::_updateBaseline(float* buf, int& idx, bool& full, float& baseline, float val) {
  buf[idx] = val;
  idx = (idx + 1) % BASELINE_WINDOW;
  if (idx == 0) full = true;
  int n = full ? BASELINE_WINDOW : (idx > 0 ? idx : 1);
  float sum = 0.0f;
  for (int i = 0; i < n; i++) sum += buf[i];
  baseline = sum / n;
}

void AudioManager::read(AudioData &data) {
  // ── MAX9814 analog ────────────────────────────────────────
  long sumSq = 0;
  int  peak  = 0;
  for (int i = 0; i < ANALOG_N; i++) {
    int v = analogRead(MIC_ANALOG_PIN) - 2048;
    sumSq += (long)v * v;
    if (abs(v) > peak) peak = abs(v);
    // ESP32-S3 ADC sample-and-hold settles in ~3 µs — the 50 µs delay
    // here was costing us 12.8 ms of blocking per audio cycle for no
    // signal-quality benefit.
    delayMicroseconds(5);
  }
  data.analogRMS  = sqrt((float)sumSq / ANALOG_N);
  data.analogPeak = (float)peak;

  // ── INMP441 I2S ───────────────────────────────────────────
  data.digitalRMS  = 0;
  data.digitalPeak = 0;

  if (_i2sOk) {
    int32_t buf[I2S_N];
    size_t  bytes = 0;
    if (i2s_read(I2S_NUM_0, buf, sizeof(buf),
                 &bytes, pdMS_TO_TICKS(100)) == ESP_OK
        && bytes > 0) {
      int      n    = bytes / sizeof(int32_t);
      long long sum = 0;
      int32_t  pk   = 0;
      for (int i = 0; i < n; i++) {
        int32_t s = buf[i] >> 11;
        sum += (long long)s * s;
        if (abs(s) > abs(pk)) pk = s;
      }
      data.digitalRMS  = sqrt((double)sum / n);
      data.digitalPeak = (float)abs(pk);
    }
  }

  // ── Adaptive sound detection ──────────────────────────────
  // Compare RMS against a rolling per-mic baseline, not a hard-coded
  // threshold. A sound event needs (a) significant absolute deviation
  // from the floor AND (b) a meaningful relative increase (1.5×) so a
  // quiet ambient drift doesn't flip the flag.
  float analogDelta  = data.analogRMS  - _analogBaseline;
  float digitalDelta = data.digitalRMS - _digitalBaseline;

  data.soundDetected =
    (analogDelta  > 50.0f  && data.analogRMS  > _analogBaseline  * 1.5f) ||
    (digitalDelta > 100.0f && data.digitalRMS > _digitalBaseline * 1.5f);

  // Update baselines only during quiet periods so a sustained loud event
  // doesn't bake itself in.
  if (analogDelta  < 50.0f)
    _updateBaseline(_analogBuf,  _analogIdx,  _analogFull,  _analogBaseline,  data.analogRMS);
  if (digitalDelta < 100.0f)
    _updateBaseline(_digitalBuf, _digitalIdx, _digitalFull, _digitalBaseline, data.digitalRMS);

  data.valid = true;
}
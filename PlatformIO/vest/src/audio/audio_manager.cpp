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
  Serial.println("[AUDIO] INMP441 I2S driver installed.");

  // ── Boot test read ─────────────────────────────────────────
  // Drains a few sample words right after init so we can see whether the
  // I2S peripheral is actually clocking the mic. Most "D:0 forever"
  // failures fall into one of these buckets:
  //   • err != ESP_OK              → driver / pin config issue
  //   • err == OK, bytes == 0      → DMA buffers empty, mic not clocking
  //   • err == OK, bytes > 0, raw == 0  → SD line floating / dead mic
  //   • err == OK, raw nonzero, but >>8 ~ 0  → wrong shift depth
  int32_t testBuf[64];
  size_t  bytes = 0;
  esp_err_t err = i2s_read(I2S_NUM_0, testBuf, sizeof(testBuf), &bytes, pdMS_TO_TICKS(200));
  Serial.printf("[AUDIO] I2S test read: err=%d bytes=%u\n", (int)err, (unsigned)bytes);
  if (bytes >= sizeof(int32_t)) {
    Serial.printf("[AUDIO] First raw words: 0x%08X 0x%08X 0x%08X (shifted >>8: %d %d %d)\n",
                  (unsigned)testBuf[0], (unsigned)testBuf[1], (unsigned)testBuf[2],
                  testBuf[0] >> 8, testBuf[1] >> 8, testBuf[2] >> 8);
  }
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
    esp_err_t err = i2s_read(I2S_NUM_0, buf, sizeof(buf),
                             &bytes, pdMS_TO_TICKS(100));
    if (err == ESP_OK && bytes > 0) {
      int      n    = bytes / sizeof(int32_t);
      long long sum = 0;
      int32_t  pk   = 0;
      for (int i = 0; i < n; i++) {
        // INMP441 outputs 24-bit signed audio MSB-justified in a 32-bit
        // word: bits [31:8] = sample, bits [7:0] = zero. The arithmetic
        // right-shift by 8 sign-extends and gives the true 24-bit value
        // in int32_t. The previous `>> 11` was an over-aggressive scale
        // that floored typical room-noise levels (24-bit magnitudes
        // around ±2000-10000) to zero before RMS — which is why the
        // digital mic was reporting D:0 forever.
        int32_t s = buf[i] >> 8;
        sum += (long long)s * s;
        if (abs(s) > abs(pk)) pk = s;
      }
      data.digitalRMS  = sqrt((double)sum / n);
      data.digitalPeak = (float)abs(pk);
    }

    // Periodic diagnostic — once every ~5 s. Prints the I²S read status,
    // bytes returned, the first raw word, and the resulting RMS so we can
    // tell whether the mic is silent, clocking junk, or actually working.
    static int diagCounter = 0;
    if (++diagCounter >= 5) {
      diagCounter = 0;
      Serial.printf("[AUDIO] I2S err=%d bytes=%u raw0=0x%08X rms=%.1f peak=%.1f\n",
                    (int)err, (unsigned)bytes,
                    bytes > 0 ? (unsigned)buf[0] : 0u,
                    data.digitalRMS, data.digitalPeak);
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
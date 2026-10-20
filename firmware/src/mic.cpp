// ============================================================================
// Smart Home - analog microphone on A0
//
// Part of the very same firmware as main.cpp: this file only implements the
// class declared in mic.h, which is why PlatformIO links both into one binary.
// See mic.h for why the board is only a microphone and how a phrase is cut out
// of the stream.
// ============================================================================

#include "mic.h"

Microphone microphone;

// The converter is 10 bit, so the middle of its range is 512 and one step is
// scaled by 64 to fill the 16 bit range the backend expects.
static const int16_t MIC_BIAS = 512;
static const int8_t MIC_SHIFT = 6;

void Microphone::begin(uint8_t pin) {
    _pin = pin;
    _sampleRate = MIC_SAMPLE_RATE;
    _intervalMicros = 1000000UL / _sampleRate;
    _nextSampleAt = micros();
    _maxSamples = _sampleRate * 8;
    _streamedSamples = 0;
    _armed = false;
    _streaming = false;
    _attack = 0;
    _silence = 0;
    _threshold = MIC_DEFAULT_THRESHOLD;
    _level = 0;
    _levelSentAt = millis();
    _resyncLoggedAt = 0;
    _previousRaw = 0;
    _smoothing = 0;
    _prerollSize = (_sampleRate * MIC_PREROLL_MS) / 1000;
    _prerollFill = 0;
    _prerollHead = 0;
    _chunkUsed = 0;
    _chunkEnergy = 0;
    _sender = nullptr;
    _frames = nullptr;

    // Nothing is configured on the converter on purpose: its full 10 bit range is
    // already the default, and the range the core exposes differs between versions,
    // so the board uses whatever the build gives it and the speech threshold is set
    // from the backend instead.
    Serial.printf(
        "[mic] converter ready on A0, %u Hz, pre-roll %u samples\n",
        _sampleRate,
        _prerollSize
    );
}

void Microphone::setSenders(MicSender sender, MicFrameSender frames) {
    _sender = sender;
    _frames = frames;
}

void Microphone::arm(uint16_t sampleRate, uint32_t maxMs) {
    // Only the rates this converter can actually deliver are accepted. A board
    // asked for sixteen kilohertz would fall behind forever and stream silence,
    // which looks exactly like a microphone that does not work.
    if (sampleRate != MIC_SAMPLE_RATE) {
        sampleRate = MIC_SAMPLE_RATE;
    }
    _sampleRate = sampleRate;
    _intervalMicros = 1000000UL / _sampleRate;
    _prerollSize = (_sampleRate * MIC_PREROLL_MS) / 1000;
    if (_prerollSize > MIC_PREROLL_SAMPLES) {
        _prerollSize = MIC_PREROLL_SAMPLES;
    }
    _maxSamples = (uint32_t)_sampleRate * ((maxMs == 0 ? 8000UL : maxMs) / 1000UL);
    reset();
    _armed = true;
    _nextSampleAt = micros();
    Serial.printf(
        "[mic] armed, %u Hz, up to %lu ms, speech level %u\n",
        sampleRate,
        (unsigned long)maxMs,
        _threshold
    );
}

void Microphone::disarm() {
    _armed = false;
    if (_streaming) {
        stopStream("disarmed");
    }
    reset();
    Serial.println("[mic] disarmed");
}

void Microphone::setThreshold(uint16_t threshold) {
    _threshold = threshold > 1023 ? 1023 : threshold;
    Serial.printf("[mic] speech level %u\n", _threshold);
}

void Microphone::poll() {
    if (!_armed) {
        return;
    }
    unsigned long now = micros();
    int32_t due = (int32_t)(now - _nextSampleAt);
    if (due < 0) {
        return;
    }

    // The main loop also carries the network, so a backlog is normal. Missing
    // samples are written as silence instead of being replayed: a hole of a couple
    // of milliseconds is something a recognizer does not even notice, while a
    // replayed old sample is a sample of the wrong moment.
    int32_t count = due / (int32_t)_intervalMicros + 1;
    if (count > MIC_MAX_BACKLOG_SAMPLES) {
        count = MIC_MAX_BACKLOG_SAMPLES;
        _nextSampleAt = now;
        _reportResync(now);
    }
    for (int32_t index = 0; index < count; index++) {
        _nextSampleAt += _intervalMicros;
        pushSample(index + 1 == count ? readSample() : 0, _streaming);
    }
}

void Microphone::_reportResync(unsigned long now) {
    if (now - _resyncLoggedAt < MIC_RESYNC_LOG_MS) {
        return;
    }
    _resyncLoggedAt = now;
    Serial.println("[mic] sampling fell behind, writing silence instead");
}

int16_t Microphone::readSample() {
    uint16_t raw = (uint16_t)analogRead(_pin);
    if (_smoothing == 0) {
        _smoothing = MIC_SMOOTHING - 1;
        _previousRaw = raw;
        return (int16_t)(((int32_t)raw - MIC_BIAS) << MIC_SHIFT);
    }
    _smoothing = 0;
    uint16_t average = (uint16_t)((_previousRaw + raw) / 2);
    _previousRaw = raw;
    return (int16_t)(((int32_t)average - MIC_BIAS) << MIC_SHIFT);
}

bool Microphone::levelDue() {
    unsigned long now = millis();
    if (now - _levelSentAt < MIC_LEVEL_INTERVAL_MS) {
        return false;
    }
    _levelSentAt = now;
    return true;
}

void Microphone::pushSample(int16_t sample, bool streamed) {
    if (!streamed) {
        rememberSample(sample);
    }
    addToChunk(sample);
    if (streamed) {
        _streamedSamples++;
    }
    if (_chunkUsed < MIC_PCM_BYTES) {
        return;
    }

    uint16_t rms = chunkLevel();
    _level = rms;
    if (streamed) {
        sendChunk();
        updateDetector(rms, true);
        return;
    }

    // Nothing is streamed yet, so this chunk is dropped: every sample of it is
    // already in the ring buffer, and the ring is what the phrase starts with.
    openChunk();
    updateDetector(rms, false);
}

void Microphone::rememberSample(int16_t sample) {
    if (_prerollSize == 0) {
        return;
    }
    if (_prerollFill < _prerollSize) {
        _preroll[_prerollFill++] = sample;
        return;
    }
    _preroll[_prerollHead] = sample;
    _prerollHead = (uint16_t)((_prerollHead + 1) % _prerollSize);
}

void Microphone::addToChunk(int16_t sample) {
    _chunk[_chunkUsed++] = (uint8_t)(sample & 0xFF);
    _chunk[_chunkUsed++] = (uint8_t)((sample >> 8) & 0xFF);
    int32_t magnitude = sample < 0 ? -(int32_t)sample : sample;
    _chunkEnergy += (uint32_t)magnitude;
}

void Microphone::openChunk() {
    _chunkUsed = 0;
    _chunkEnergy = 0;
}

void Microphone::sendChunk() {
    if (_sender != nullptr) {
        _sender(_chunk, MIC_PCM_BYTES);
    }
    openChunk();
}

void Microphone::updateDetector(uint16_t rms, bool streamed) {
    if (rms >= _threshold) {
        _silence = 0;
        if (!streamed) {
            if (_attack < MIC_ATTACK_CHUNKS) {
                _attack++;
            }
            if (_attack >= MIC_ATTACK_CHUNKS) {
                startStream();
            }
        }
        return;
    }

    _attack = 0;
    if (!streamed) {
        return;
    }
    if (_silence < 255) {
        _silence++;
    }
    if ((uint16_t)(_silence * MIC_CHUNK_MS) >= MIC_SILENCE_MS) {
        stopStream("silence");
        return;
    }
    if (_streamedSamples >= _maxSamples) {
        stopStream("limit");
    }
}

void Microphone::startStream() {
    _streaming = true;
    _streamedSamples = 0;
    _silence = 0;
    _attack = 0;

    char frame[96];
    snprintf(
        frame,
        sizeof(frame),
        "{\"type\":\"AUDIO_START\",\"sample_rate\":%u,\"format\":\"pcm_s16le\"}",
        _sampleRate
    );
    if (_frames != nullptr) {
        _frames(frame);
    }
    Serial.printf("[mic] speech detected, level %u\n", _level);
    flushPreroll();
}

void Microphone::stopStream(const char *reason) {
    if (!_streaming) {
        return;
    }
    _streaming = false;

    char frame[96];
    snprintf(
        frame,
        sizeof(frame),
        "{\"type\":\"AUDIO_STOP\",\"reason\":\"%s\",\"level\":%u,\"threshold\":%u}",
        reason,
        _level,
        _threshold
    );
    if (_frames != nullptr) {
        _frames(frame);
    }
    Serial.printf(
        "[mic] phrase closed (%s), %lu samples\n", reason, (unsigned long)_streamedSamples
    );
    _streamedSamples = 0;
    _prerollFill = 0;
    _prerollHead = 0;
    _silence = 0;
    _attack = 0;
    openChunk();
}

void Microphone::flushPreroll() {
    if (_sender == nullptr || _prerollSize == 0) {
        _prerollFill = 0;
        _prerollHead = 0;
        return;
    }
    uint16_t oldest = _prerollFill < _prerollSize
                          ? 0
                          : (uint16_t)((_prerollHead + _prerollSize - _prerollFill) % _prerollSize);
    for (uint16_t index = 0; index < _prerollFill; index++) {
        addToChunk(_preroll[oldest]);
        oldest = (uint16_t)((oldest + 1) % _prerollSize);
        _streamedSamples++;
        if (_chunkUsed >= MIC_PCM_BYTES) {
            sendChunk();
        }
    }
    _prerollFill = 0;
    _prerollHead = 0;
}

void Microphone::reset() {
    _streaming = false;
    _streamedSamples = 0;
    _prerollFill = 0;
    _prerollHead = 0;
    _attack = 0;
    _silence = 0;
    openChunk();
}

uint16_t Microphone::chunkLevel() const {
    uint16_t used = _chunkUsed / 2;
    if (used == 0) {
        return 0;
    }
    // The samples are scaled to 16 bit while the threshold lives in the 10 bit
    // range of the converter, so the loudness is scaled back before comparing.
    uint32_t mean = _chunkEnergy / used;
    return (uint16_t)(mean >> MIC_SHIFT);
}
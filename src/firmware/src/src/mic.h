// ============================================================================
// Smart Home - analog microphone on A0
//
// The board is a microphone and nothing more: it samples its analog input, finds
// out where a phrase starts and where it ends, and streams raw samples to the
// backend. Recognition runs on another machine, so no model ever lives here.
//
// WHY IT IS SO PLAIN
//
// The ESP8266 converter is 10 bit and has no DMA: reading it means a plain
// analogRead in a tight loop, and the Wi-Fi interrupts land in the middle of that
// loop. Nothing clever can be done about that, so the code aims at the two things
// that do help:
//
//   1. every sample is the average of four reads, which halves the noise;
//   2. the signal is streamed in small chunks of 20 ms, so a lost TCP segment
//      costs a fifth of a second instead of the whole phrase.
//
// A low pass in front of A0 (about 3 kHz, a 10 nF capacitor and a 5.1 kΩ
// resistor) keeps the aliasing out. See docs/hardware/esp-protocol.md.
//
// WHEN AUDIO FLOWS
//
// The backend opens the recording window with ARM_MIC and closes it with
// DISARM_MIC. A board that streamed by itself would push 32 KB/s through a home
// Wi-Fi every second of every day, so nothing is sent until the backend asks.
// Inside the window the board still decides where the phrase is: it keeps the
// last 200 ms in a ring buffer and flushes it first, which keeps the first
// syllable from being cut off.
//
// NO Arduino String ANYWHERE, like the rest of the firmware: it reallocates on
// the heap and this chip dies of the resulting fragmentation with Exception (29)
// LoadStoreError.
// ============================================================================

#ifndef MIC_H
#define MIC_H

#include <Arduino.h>

// Rate the converter can actually deliver on this chip, and the honest answer is
// four kilohertz.
//
// A single analogRead takes about 100 microseconds, and on top of that every Wi-Fi
// packet interrupts the loop. Eight kilohertz would need 125 microseconds per
// sample, which leaves nothing: the board fell behind continuously and streamed
// silence with a few real samples in it. Four kilohertz gives 250, which the loop
// keeps up with even while the radio is busy.
//
// Speech is 300 to 3400 Hz, so this is the telephone band with the top edge just
// touched, and it is what recognition has always been trained on. Anything above it
// on this chip buys silence instead of clarity.
static const uint16_t MIC_SAMPLE_RATE = 4000;

// Two samples averaged in software instead of four reads in a row: averaging by
// reading four times cannot work at any useful rate, while keeping the previous
// value and averaging costs nothing and still removes the quantisation step.
static const uint8_t MIC_SMOOTHING = 2;

// One streamed chunk. Forty milliseconds is two percent of a second and a quarter
// of the work per sample than a shorter chunk would need, because the transport is
// called once per chunk and not once per twenty milliseconds of life.
static const uint16_t MIC_CHUNK_MS = 40;

// Samples per chunk, derived from the period above.
static const uint16_t MIC_CHUNK_SAMPLES = (MIC_CHUNK_MS * MIC_SAMPLE_RATE / 1000);

// Audio kept before the speech detector fires, so the phrase starts with its
// first syllable instead of halfway through it.
static const uint16_t MIC_PREROLL_MS = 200;

// Samples of the pre-roll, which is what the ring buffer of the board costs: at
// four kilohertz 800 samples are 1.6 kB, a thirtieth of the heap the socket needs.
static const uint16_t MIC_PREROLL_SAMPLES = (MIC_SAMPLE_RATE * MIC_PREROLL_MS) / 1000;

// How often the board admits in the serial log that it is falling behind. The
// message is worth having and is still able to cause the fall behind, so it is rare
// on purpose: printing it every time turns one hiccup into a permanent lag.
static const unsigned long MIC_RESYNC_LOG_MS = 5000;

// How long the level has to stay below the threshold before the phrase is over.
static const uint16_t MIC_SILENCE_MS = 700;

// How long the level has to stay above the threshold before it counts as speech.
// Two chunks are 40 ms, which ignores a click of the relay.
static const uint8_t MIC_ATTACK_CHUNKS = 2;

// Loudness above which the board considers it speech, within the 10 bit range of
// the converter. The backend sends SET_VAD, because the right value depends on
// the gain of the module and has to be tuned on the real hardware.
static const uint16_t MIC_DEFAULT_THRESHOLD = 180;

// How often the loudness is reported while the window is open. It is what you
// watch while setting the gain of the module: the level has to sit clearly below
// the threshold in silence and clearly above it while speaking.
static const unsigned long MIC_LEVEL_INTERVAL_MS = 2000;

// Longest backlog that is treated as a delay rather than a stall.
static const uint16_t MIC_MAX_BACKLOG_SAMPLES = 160;

static const uint16_t MIC_PCM_BYTES = 2 * MIC_CHUNK_SAMPLES;

// Signature of the sender the microphone streams through. main.cpp hands over a
// function writing one binary WebSocket frame, so this file knows nothing about
// the transport.
typedef void (*MicSender)(const uint8_t *data, size_t length);

// Signature of the frame sender used for the text control frames.
typedef void (*MicFrameSender)(const char *frame);

// ============================================================================
// Microphone
// ============================================================================
class Microphone {
   public:
    /** Prepare the converter and start the sampling clock.
     *
     * Args:
     *     pin: Analog input the module is wired to.
     *
     * Returns:
     *     None.
     */
    void begin(uint8_t pin);

    /** Route the samples and the control frames out of this class.
     *
     * Args:
     *     sender: Writes one binary frame with raw samples.
     *     frames: Writes one text frame, used for the control messages.
     *
     * Returns:
     *     None.
     */
    void setSenders(MicSender sender, MicFrameSender frames);

    /** Open the recording window requested by the backend.
     *
     * Args:
     *     sampleRate: Samples per second to sample with.
     *     maxMs: Longest phrase that may be streamed.
     *
     * Returns:
     *     None.
     */
    void arm(uint16_t sampleRate, uint32_t maxMs);

    /** Close the recording window and forget what was collected.
     *
     * Returns:
     *     None.
     */
    void disarm();

    /** Change the loudness above which the board sees speech.
     *
     * Args:
     *     threshold: Threshold within the 10 bit range of the converter.
     *
     * Returns:
     *     None.
     */
    void setThreshold(uint16_t threshold);

    /** Read the samples that are due and stream them when a phrase is running.
     *
     * Called from the main loop as often as possible: it is the only thing that
     * samples the converter, and the loop also carries the network, so a late
     * call is a missed sample.
     *
     * Returns:
     *     None.
     */
    void poll();

    /** Return whether the recording window is open.
     *
     * Returns:
     *     bool: True while the backend listens.
     */
    bool isArmed() const { return _armed; }

    /** Return whether a phrase is being streamed right now.
     *
     * Returns:
     *     bool: True between the first and the last chunk of a phrase.
     */
    bool isStreaming() const { return _streaming; }

    /** Return the loudness of the last completed chunk.
     *
     * Returns:
     *     uint16_t: Level within the 10 bit range of the converter.
     */
    uint16_t level() const { return _level; }

    /** Return the loudness above which the board sees speech.
     *
     * Returns:
     *     uint16_t: Threshold within the 10 bit range of the converter.
     */
    uint16_t threshold() const { return _threshold; }

    /** Return whether the loudness is due to be reported.
     *
     * Returns:
     *     bool: True once per reporting period.
     */
    bool levelDue();

   private:
    /** Sample the converter once, averaging it with the previous read.

    Returns:
        int16_t: Sample centred on zero and scaled to 16 bit.
    */
    int16_t readSample();

    /** Admit once in a while in the serial log that sampling cannot keep up.

    The main loop carries the network as well, so a short backlog is normal and a
    long one only happens when something else took the CPU. Writing silence for
    the missing samples keeps the stream honest, and saying so once in a while
    makes the cause visible without becoming the cause itself.

    Args:
        now: Current value of millis.

    Returns:
        None.
    */
    void _reportResync(unsigned long now);

    /** Store one sample and act on the chunk that just filled up.
     *
     * Args:
     *     sample: Sample to store.
     *     streamed: Whether a phrase is being streamed already.
     *
     * Returns:
     *     None.
     */
    void pushSample(int16_t sample, bool streamed);

    /** Remember a sample in the ring buffer of the pre-roll.
     *
     * Args:
     *     sample: Sample to remember.
     *
     * Returns:
     *     None.
     */
    void rememberSample(int16_t sample);

    /** Update the speech detector with the loudness of a completed chunk.
     *
     * Args:
     *     rms: Loudness within the 10 bit range of the converter.
     *     streamed: Whether a phrase is being streamed already.
     *
     * Returns:
     *     None.
     */
    void updateDetector(uint16_t rms, bool streamed);

    /** Open a chunk of raw samples for writing.
     *
     * Returns:
     *     None.
     */
    void openChunk();

    /** Add one sample to the chunk being built.
     *
     * Args:
     *     sample: Sample to add.
     *
     * Returns:
     *     None.
     */
    void addToChunk(int16_t sample);

    /** Send the samples of the ring buffer as the beginning of a phrase.
     *
     * Returns:
     *     None.
     */
    void flushPreroll();

    /** Start streaming a phrase.
     *
     * Returns:
     *     None.
     */
    void startStream();

    /** Stop streaming and tell the backend why.
     *
     * Args:
     *     reason: Machine readable reason, for example silence.
     *
     * Returns:
     *     None.
     */
    void stopStream(const char *reason);

    /** Forget everything collected so far.
     *
     * Returns:
     *     None.
     */
    void reset();

    /** Compute the loudness of the chunk being built.
     *
     * Returns:
     *     uint16_t: Level within the 10 bit range of the converter.
     */
    uint16_t chunkLevel() const;

    /** Send one binary frame of samples.
     *
     * Returns:
     *     None.
     */
    void sendChunk();

    uint8_t _pin;
    uint16_t _sampleRate;
    uint32_t _intervalMicros;
    uint32_t _nextSampleAt;
    uint32_t _maxSamples;
    uint32_t _streamedSamples;

    bool _armed;
    bool _streaming;
    uint8_t _attack;
    uint8_t _silence;
    uint16_t _threshold;
    uint16_t _level;
    unsigned long _levelSentAt;
    unsigned long _resyncLoggedAt;
    uint16_t _previousRaw;
    uint8_t _smoothing;

    uint16_t _chunkUsed;
    uint32_t _chunkEnergy;
    uint8_t _chunk[MIC_PCM_BYTES];

    uint16_t _prerollSize;
    uint16_t _prerollFill;
    uint16_t _prerollHead;
    int16_t _preroll[MIC_PREROLL_SAMPLES];

    MicSender _sender;
    MicFrameSender _frames;
};

extern Microphone microphone;

#endif  // MIC_H
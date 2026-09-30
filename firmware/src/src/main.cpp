// ============================================================================
// Smart Home - ESP8266 firmware
//
// The board is an executor and a data source: it joins Wi-Fi, drives six relay
// channels, reads the DHT22, executes commands from the backend and reports its
// state back. Automation, scenarios, storage and natural language all live in
// backend, and so does every decision: the board never picks a device.
//
// TWO BUILD MODES
//
// Set SERVE_WEB_INTERFACE to 0 when a separate machine runs the backend and
// serves the interface, which is the recommended setup: a Raspberry Pi hands out
// the full page and the WebSocket works natively, so nothing has to be proxied
// and the board stays a pure driver.
//
// Set it to 1 when the board is the only host in the system. It then serves a
// compact page itself and forwards the API calls to the backend, so a user can
// reach the home through it without running anything locally. In this mode only
// the web port has to be reachable from outside.
//
// IMPORTANT IMPLEMENTATION NOTES
//
// 1. No Arduino String anywhere. Strings reallocate on the heap, and on this
//    chip the resulting fragmentation crashes with Exception (29)
//    LoadStoreError. Every frame and every proxy buffer is a fixed char array.
//
// 2. The backend address must be numeric and is passed as an IPAddress.
//    Resolving a hostname calls WiFi.hostByName, which is unreliable here.
//
// 3. Serial noise at 74880 baud is the boot ROM, not a fault. Read the board
//    at 115200 for our own output.
//
// Pinout (fixed in firmware, backend only maps channels to logical devices):
//   D1 (GPIO5)  -> Relay 1
//   D2 (GPIO4)  -> Relay 2
//   D3 (GPIO0)  -> Relay 3
//   D4 (GPIO2)  -> Relay 4
//   D5 (GPIO14) -> Relay 5
//   D6 (GPIO12) -> Relay 6
//   D7 (GPIO13) -> DHT22 DATA (VCC -> 3.3V, GND -> GND)
//
// Relay modules are active low: LOW energises the relay, HIGH releases it.
// D4 (GPIO2) is a bootstrap pin, so relay 4 is briefly energised while the
// board boots. Channels can be reassigned in backend without reflashing.
// ============================================================================

#include <Arduino.h>
#include <DHT.h>
#include <ESP8266WiFi.h>
#include <ESP8266WiFiMulti.h>
#include <WebSocketsClient.h>

#ifndef SERVE_WEB_INTERFACE
#define SERVE_WEB_INTERFACE 1
#endif

#if SERVE_WEB_INTERFACE
#include <ESP8266WebServer.h>
#include "ui.h"
#endif

// ---------------------------------------------------------------------------
// Configuration, edit here and flash
// ---------------------------------------------------------------------------
static const char *WIFI_SSID = "sweet_home";
static const char *WIFI_PASS = "gelenvagen94";

// Numeric address of the machine running backend. No DNS lookup happens.
static const char *BACKEND_HOST = "192.168.0.141";

// WebSocket port of backend: the board subscribes to events over it.
static const uint16_t BACKEND_WS_PORT = 8765;
static const char *BACKEND_PATH = "/esp";

#if SERVE_WEB_INTERFACE
// HTTP port of backend: the board proxies the interface requests to it.
static const uint16_t BACKEND_HTTP_PORT = 8000;
static const uint16_t WEB_PORT = 80;
#endif

static const unsigned long TELEMETRY_INTERVAL_MS = 5000;
static const unsigned long DHT_INTERVAL_MS = 2000;
static const unsigned long WIFI_TIMEOUT_MS = 20000;
static const unsigned long SOCKET_RETRY_MS = 3000;
#if SERVE_WEB_INTERFACE
static const unsigned long PROXY_TIMEOUT_MS = 4000;
#endif

// ---------------------------------------------------------------------------
// Hardware
// ---------------------------------------------------------------------------
static const uint8_t RELAY_PINS[6] = {5, 4, 0, 2, 14, 12}; // D1..D6
static const uint8_t RELAY_COUNT = 6;
static const bool RELAY_ACTIVE_LOW = true;
static const uint8_t DHT_PIN = 13; // D7
static const uint8_t DHT_TYPE = DHT22;

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
static const char *FIRMWARE_VERSION = "1.1.0";
static const int PROTOCOL_VERSION = 1;
static const size_t FRAME_SIZE = 192;

ESP8266WiFiMulti wifi;
WebSocketsClient socket;
DHT dht(DHT_PIN, DHT_TYPE);

#if SERVE_WEB_INTERFACE
static const size_t REQUEST_BODY_SIZE = 256;
static const size_t RESPONSE_SIZE = 3072;
static const size_t CHUNK_SIZE = 256;
ESP8266WebServer web(WEB_PORT);
static char requestBody[REQUEST_BODY_SIZE];
static char response[RESPONSE_SIZE];
#endif

static bool relayOn[RELAY_COUNT] = {false, false, false, false, false, false};
static float temperature = NAN;
static float humidity = NAN;

static unsigned long lastTelemetryAt = 0;
static unsigned long lastDhtReadAt = 0;
static unsigned long lastSocketTryAt = 0;
static bool socketStarted = false;
static char frame[FRAME_SIZE];

// ---------------------------------------------------------------------------
// Sensor
// ---------------------------------------------------------------------------
bool sensorsReady() {
    return !isnan(temperature) && !isnan(humidity);
}

void readDht() {
    unsigned long now = millis();
    if (now - lastDhtReadAt < DHT_INTERVAL_MS) {
        return;
    }
    lastDhtReadAt = now;

    float currentTemperature = dht.readTemperature();
    float currentHumidity = dht.readHumidity();
    if (isnan(currentTemperature) || isnan(currentHumidity)) {
        return;
    }
    temperature = currentTemperature;
    humidity = currentHumidity;
}

// ---------------------------------------------------------------------------
// Frame building, always into the shared buffer
// ---------------------------------------------------------------------------
void putRelays(char *out, size_t capacity) {
    size_t offset = 0;
    out[0] = '\0';
    for (uint8_t index = 0; index < RELAY_COUNT; index++) {
        int written = snprintf(
            out + offset,
            capacity - offset,
            "%s%s",
            index == 0 ? "" : ",",
            relayOn[index] ? "true" : "false"
        );
        if (written < 0 || (size_t)written >= capacity - offset) {
            break;
        }
        offset += (size_t)written;
    }
}

void sendState() {
    char relays[64];
    putRelays(relays, sizeof(relays));
    if (sensorsReady()) {
        snprintf(
            frame,
            FRAME_SIZE,
            "{\"type\":\"STATE\",\"relays\":[%s],\"temperature\":%.2f,\"humidity\":%.2f}",
            relays,
            temperature,
            humidity
        );
    } else {
        snprintf(frame, FRAME_SIZE, "{\"type\":\"STATE\",\"relays\":[%s]}", relays);
    }
    socket.sendTXT(frame);
}

void sendHello() {
    char relays[64];
    putRelays(relays, sizeof(relays));
    snprintf(
        frame,
        FRAME_SIZE,
        "{\"type\":\"HELLO\",\"firmware_version\":\"%s\",\"protocol_version\":%d,\"relays\":[%s]}",
        FIRMWARE_VERSION,
        PROTOCOL_VERSION,
        relays
    );
    socket.sendTXT(frame);
}

void sendSensorData() {
    snprintf(
        frame,
        FRAME_SIZE,
        "{\"type\":\"SENSOR_DATA\",\"temperature\":%.2f,\"humidity\":%.2f}",
        temperature,
        humidity
    );
    socket.sendTXT(frame);
}

void sendAck(const char *commandId) {
    snprintf(frame, FRAME_SIZE, "{\"type\":\"ACK\",\"command_id\":\"%s\"}", commandId);
    socket.sendTXT(frame);
}

void sendError(const char *code, const char *message) {
    snprintf(frame, FRAME_SIZE, "{\"type\":\"ERROR\",\"code\":\"%s\",\"message\":\"%s\"}", code, message);
    socket.sendTXT(frame);
}

// ---------------------------------------------------------------------------
// Relays
// ---------------------------------------------------------------------------
void writeRelayPin(uint8_t index, bool on) {
    digitalWrite(RELAY_PINS[index], RELAY_ACTIVE_LOW ? !on : on);
}

void setRelay(uint8_t channel, bool on) {
    if (channel < 1 || channel > RELAY_COUNT) {
        return;
    }
    relayOn[channel - 1] = on;
    writeRelayPin(channel - 1, on);
    Serial.printf("[relay] channel %u -> %s\n", channel, on ? "ON" : "OFF");
}

// ---------------------------------------------------------------------------
// Minimal JSON reader for the flat command frames
// ---------------------------------------------------------------------------
bool readStringField(const char *json, const char *key, char *out, size_t capacity) {
    char pattern[32];
    snprintf(pattern, sizeof(pattern), "\"%s\":", key);
    const char *start = strstr(json, pattern);
    if (start == NULL) {
        return false;
    }
    const char *value = start + strlen(pattern);
    while (*value == ' ') {
        value++;
    }
    if (*value != '"') {
        return false;
    }
    value++;
    size_t index = 0;
    while (*value != '"' && *value != '\0' && index + 1 < capacity) {
        out[index++] = *value++;
    }
    out[index] = '\0';
    return true;
}

bool readIntField(const char *json, const char *key, int *out) {
    char pattern[32];
    snprintf(pattern, sizeof(pattern), "\"%s\":", key);
    const char *start = strstr(json, pattern);
    if (start == NULL) {
        return false;
    }
    const char *value = start + strlen(pattern);
    while (*value == ' ') {
        value++;
    }
    if (*value < '0' || *value > '9') {
        return false;
    }
    *out = atoi(value);
    return true;
}

bool readBoolField(const char *json, const char *key, bool *out) {
    char pattern[32];
    snprintf(pattern, sizeof(pattern), "\"%s\":", key);
    const char *start = strstr(json, pattern);
    if (start == NULL) {
        return false;
    }
    const char *value = start + strlen(pattern);
    while (*value == ' ') {
        value++;
    }
    *out = strncmp(value, "true", 4) == 0 || *value == '1';
    return true;
}

// ---------------------------------------------------------------------------
// Command handling
// ---------------------------------------------------------------------------
void handleSetRelay(const char *message) {
    int channel = 0;
    bool on = false;
    if (!readIntField(message, "channel", &channel) ||
        !readBoolField(message, "state", &on)) {
        sendError("BAD_COMMAND", "missing channel or state");
        return;
    }
    if (channel < 1 || channel > RELAY_COUNT) {
        sendError("BAD_CHANNEL", "channel out of range 1..6");
        return;
    }

    char commandId[32] = "";
    readStringField(message, "command_id", commandId, sizeof(commandId));

    setRelay((uint8_t)channel, on);
    sendAck(commandId);
    sendState();
}

void handleIncoming(const char *message) {
    char type[24] = "";
    if (!readStringField(message, "type", type, sizeof(type))) {
        sendError("BAD_MESSAGE", "missing type");
        return;
    }
    if (strcmp(type, "SET_RELAY") == 0) {
        handleSetRelay(message);
        return;
    }
    if (strcmp(type, "GET_STATE") == 0) {
        readDht();
        sendState();
        return;
    }
    sendError("UNKNOWN_TYPE", "unsupported message type");
}

#if SERVE_WEB_INTERFACE
// ---------------------------------------------------------------------------
// Embedded web interface
//
// The board is the only host the user has to reach, so it serves the page and
// forwards the API calls. Nothing here makes a decision: a relay is switched
// because the backend said so, and every answer is the backend's own payload.
// ---------------------------------------------------------------------------

bool resolveBackend(IPAddress *out) {
    return out->fromString(String(BACKEND_HOST));
}

void servePage() {
    web.sendHeader("Cache-Control", "no-store");
    web.send_P(200, "text/html; charset=utf-8", INDEX_HTML);
}


/** Return the offset of the empty line that ends the response headers. */
size_t headerBoundary(const char *data, size_t length) {
    for (size_t i = 0; i + 3 < length; i++) {
        if (data[i] == '\r' && data[i + 1] == '\n' && data[i + 2] == '\r' && data[i + 3] == '\n') {
            return i;
        }
    }
    return 0;
}

/** Copy a header value into a buffer, trimmed. The name match ignores case. */
bool readHeaderValue(
    const char *data,
    size_t length,
    const char *name,
    char *out,
    size_t capacity
) {
    size_t nameLength = strlen(name);
    size_t offset = 0;
    while (offset + nameLength + 2 < length) {
        if (data[offset] == '\r' && data[offset + 1] == '\n') {
            offset += 2;
            continue;
        }
        bool match = true;
        for (size_t i = 0; i < nameLength; i++) {
            char left = data[offset + i];
            char right = name[i];
            if (left >= 'A' && left <= 'Z') {
                left += 32;
            }
            if (right >= 'A' && right <= 'Z') {
                right += 32;
            }
            if (left != right) {
                match = false;
                break;
            }
        }
        if (match && data[offset + nameLength] == ':') {
            size_t cursor = offset + nameLength + 1;
            while (cursor < length && data[cursor] == ' ') {
                cursor++;
            }
            size_t written = 0;
            while (cursor < length && data[cursor] != '\r' && data[cursor] != '\n' &&
                   written + 1 < capacity) {
                out[written++] = data[cursor++];
            }
            out[written] = '\0';
            return true;
        }
        while (offset < length && data[offset] != '\r' && data[offset] != '\n') {
            offset++;
        }
    }
    return false;
}

/**
 * Forward a request to backend and return its answer to the browser.
 *
 * The answer is read into one buffer so the headers can be separated from the
 * body: the browser needs the status and the content type, and the interface
 * needs the body itself. Streaming would save memory but would leave the two
 * halves unseparated, which produced malformed replies.
 */
void proxy() {
    IPAddress backend;
    if (!resolveBackend(&backend)) {
        web.send(502, "application/json", "{\"detail\":\"backend address is not numeric\"}");
        return;
    }

    WiFiClient client;
    if (!client.connect(backend, (int)BACKEND_HTTP_PORT)) {
        web.send(502, "application/json", "{\"detail\":\"backend is unreachable\"}");
        return;
    }

    size_t requestLength = 0;
    requestBody[0] = '\0';
    if (web.hasArg("plain")) {
        requestLength = web.arg("plain").length();
        if (requestLength >= REQUEST_BODY_SIZE) {
            requestLength = REQUEST_BODY_SIZE - 1;
        }
        memcpy(requestBody, web.arg("plain").c_str(), requestLength);
        requestBody[requestLength] = '\0';
    }

    client.printf(
        "%s %s HTTP/1.1\r\n"
        "Host: %s:%u\r\n"
        "Connection: close\r\n"
        "Content-Type: application/json\r\n"
        "Content-Length: %u\r\n"
        "\r\n",
        web.method() == HTTP_POST ? "POST" : "GET",
        web.uri().c_str(),
        BACKEND_HOST,
        BACKEND_HTTP_PORT,
        (unsigned int)requestLength
    );
    if (requestLength > 0) {
        client.write((const uint8_t *)requestBody, requestLength);
    }

    unsigned long deadline = millis() + PROXY_TIMEOUT_MS;
    size_t used = 0;
    size_t split = 0;
    size_t expected = 0;
    bool lengthKnown = false;

    while (millis() < deadline) {
        size_t room = RESPONSE_SIZE - 1 - used;
        if (room == 0) {
            break;
        }
        size_t want = room < CHUNK_SIZE ? room : CHUNK_SIZE;
        int received = client.readBytes(response, want);
        if (received <= 0) {
            if (!client.connected()) {
                break;
            }
            delay(2);
            continue;
        }
        used += (size_t)received;
        response[used] = '\0';
        if (split == 0) {
            split = headerBoundary(response, used);
            if (split > 0) {
                char value[32];
                if (readHeaderValue(response, split, "content-length", value, sizeof(value))) {
                    expected = (size_t)atol(value);
                    lengthKnown = true;
                }
            }
        }
        if (split > 0 && (!lengthKnown || used - (split + 4) >= expected)) {
            break;
        }
    }

    client.stop();
    response[used] = '\0';

    if (split == 0) {
        web.send(502, "application/json", "{\"detail\":\"backend sent no usable answer\"}");
        return;
    }

    int statusCode = 200;
    if (sscanf(response, "HTTP/%*d.%*d %d", &statusCode) != 1) {
        statusCode = 200;
    }

    char contentType[64];
    if (!readHeaderValue(response, split, "content-type", contentType, sizeof(contentType)) ||
        contentType[0] == '\0') {
        strcpy(contentType, "application/json");
    }

    size_t bodyStart = split + 4;
    size_t bodyLength = used - bodyStart;
    if (lengthKnown && bodyLength > expected) {
        bodyLength = expected;
    }

    web.sendHeader("Cache-Control", "no-store");
    web.send(statusCode, contentType, bodyLength > 0 ? response + bodyStart : "", bodyLength);
}

void startWeb() {
    web.on("/", HTTP_GET, servePage);
    web.on("/api/state", HTTP_GET, proxy);
    web.on("/api/health", HTTP_GET, proxy);
    web.on("/api/scenarios", HTTP_ANY, proxy);
    web.on("/api/commands", HTTP_POST, proxy);
    web.on("/api/devices/[0-9]+/on", HTTP_POST, proxy);
    web.on("/api/devices/[0-9]+/off", HTTP_POST, proxy);
    web.on("/api/devices/[0-9]+/mode", HTTP_POST, proxy);
    web.onNotFound(proxy);
    web.begin();
    Serial.printf("[web] serving on port %u\n", WEB_PORT);
}

void handleWeb() {
    web.handleClient();
}
#endif

// ---------------------------------------------------------------------------
// WebSocket
// ---------------------------------------------------------------------------
void onSocketEvent(WStype_t type, uint8_t *payload, size_t length) {
    (void)length;
    switch (type) {
        case WStype_CONNECTED:
            Serial.println("[ws] connected to backend");
            readDht();
            sendHello();
            sendState();
            break;
        case WStype_DISCONNECTED:
            Serial.println("[ws] disconnected");
            break;
        case WStype_TEXT:
            handleIncoming((const char *)payload);
            break;
        default:
            break;
    }
}

void startSocket() {
    IPAddress backend;
    if (!backend.fromString(String(BACKEND_HOST))) {
        Serial.printf("[ws] BACKEND_HOST must be numeric, got %s\n", BACKEND_HOST);
        socketStarted = true;
        return;
    }
    socket.begin(backend, BACKEND_WS_PORT, BACKEND_PATH);
    socket.onEvent(onSocketEvent);
    socketStarted = true;
    lastSocketTryAt = millis();
    Serial.printf("[ws] connecting to %s:%u\n", BACKEND_HOST, BACKEND_WS_PORT);
}

void maintainSocket() {
    if (WiFi.status() != WL_CONNECTED) {
        socketStarted = false;
        return;
    }
    if (socketStarted) {
        return;
    }
    unsigned long now = millis();
    if (lastSocketTryAt != 0 && now - lastSocketTryAt < SOCKET_RETRY_MS) {
        return;
    }
    startSocket();
}

void sendTelemetry() {
    if (!socket.isConnected()) {
        return;
    }
    unsigned long now = millis();
    if (now - lastTelemetryAt < TELEMETRY_INTERVAL_MS) {
        return;
    }
    lastTelemetryAt = now;

    readDht();
    if (sensorsReady()) {
        Serial.printf("[dht] %.1f C %.1f %%\n", temperature, humidity);
        sendSensorData();
    } else {
        Serial.println("[dht] no valid reading, check wiring of D7");
    }
}

// ---------------------------------------------------------------------------
// Setup and loop
// ---------------------------------------------------------------------------
void setup() {
    Serial.begin(115200);
    delay(200);
    Serial.println();
    Serial.println("[boot] smart home esp8266 firmware");
    Serial.printf("[boot] free heap %u\n", ESP.getFreeHeap());

    for (uint8_t index = 0; index < RELAY_COUNT; index++) {
        pinMode(RELAY_PINS[index], OUTPUT);
        writeRelayPin(index, false);
    }

    dht.begin();

    WiFi.mode(WIFI_STA);
    wifi.addAP(WIFI_SSID, WIFI_PASS);

    Serial.print("[wifi] connecting");
    unsigned long startedAt = millis();
    while (WiFi.status() != WL_CONNECTED) {
        delay(250);
        Serial.print('.');
        wifi.run();
        if (millis() - startedAt > WIFI_TIMEOUT_MS) {
            Serial.println();
            Serial.println("[wifi] timed out, restarting");
            ESP.restart();
        }
    }
    Serial.println();
    Serial.print("[wifi] connected, ip=");
    Serial.println(WiFi.localIP());

    readDht();
    if (sensorsReady()) {
        Serial.printf("[dht] %.1f C %.1f %%\n", temperature, humidity);
    } else {
        Serial.println("[dht] no reading yet, check wiring of D7");
    }

    #if SERVE_WEB_INTERFACE
    startWeb();
#else
    Serial.println("[web] disabled, the interface is served by backend");
#endif
    Serial.printf("[boot] free heap %u\n", ESP.getFreeHeap());
}

void loop() {
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("[wifi] lost connection, reconnecting");
        socketStarted = false;
        wifi.run();
    }
#if SERVE_WEB_INTERFACE
    handleWeb();
#endif
    socket.loop();
    maintainSocket();
    sendTelemetry();
}

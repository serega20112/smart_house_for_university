// ============================================================================
// Smart Home - ESP8266 firmware
//
// The board is an executor and a data source: it joins Wi-Fi, drives six relay
// channels, reads the DHT22, executes commands from the backend and reports its
// state back. Automation, scenarios, storage and natural language all live in the
// backend and on the machine running the models, and so does every decision: the
// board never picks a device.
//
// NOTHING IS HARDCODED
//
// There is no network name, no password and no address of the server in this
// file. A board that has never been set up raises an access point of its own
// and serves a small page from it: the person walks up to the board, joins that
// access point, fills in the form, and the board writes the values into its own
// flash. It then joins the network, puts the access point away and behaves like
// every other board.
//
// The backend can change the same values later: it sends SET_NETWORK over the
// socket, and the board stores what it receives and reconnects. Both ways end
// in the same place, in the flash of the chip.
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
#include <WebSocketsClient.h>

#include "config_store.h"
#include "network_config.h"
#include "provisioning.h"

#ifndef SERVE_WEB_INTERFACE
#define SERVE_WEB_INTERFACE 1
#endif

#if SERVE_WEB_INTERFACE
#include <ESP8266WebServer.h>
#include "ui.h"
#endif

// ---------------------------------------------------------------------------
// Configuration
//
// The network of the board and the address of the server are not written here:
// they are written by the person who owns the board, into the flash of the
// chip. The only values that stay in the code are the shapes of those values:
// how long a name may be and which port a socket lives on.
// ---------------------------------------------------------------------------
static NetworkConfig network;

// ---------------------------------------------------------------------------
// Hardware
// ---------------------------------------------------------------------------
static const uint8_t RELAY_PINS[6] = {5, 4, 0, 2, 14, 12}; // D1..D6
static const uint8_t RELAY_COUNT = 6;
static const bool RELAY_ACTIVE_LOW = true;
static const uint8_t DHT_PIN = 13; // D7
static const uint8_t DHT_TYPE = DHT22;

// FLASH button of every ESP8266 board. On this wiring it shares the pin with
// relay 3, which is why holding it while powering up also closes that relay.
static const uint8_t FLASH_BUTTON_PIN = 0;

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
static const char *FIRMWARE_VERSION = "1.5.0";
static const int PROTOCOL_VERSION = 4;
// The handshake carries a 32 character key, the whole relay vector and the name
// of the network, so the buffer is sized with room to spare. Cutting a frame
// short turns it into invalid JSON, and the board then looks like it never
// dialled in at all.
static const size_t FRAME_SIZE = 320;

// How long the board asks for an owner, and how long it waits before asking
// again. The ask is a gesture on the board itself: hold FLASH while plugging the
// power in. FLASH is the button next to the USB port and is wired to GPIO0,
// which on this wiring is also relay 3, so holding it while powering up briefly
// closes that one relay. A board that already belongs to an account does not
// ask, so the gesture cannot steal it.
static const uint32_t CLAIM_WINDOW_MS = 120000;
static const unsigned long CLAIM_RETRY_MS = 5000;

static const unsigned long TELEMETRY_INTERVAL_MS = 5000;
static const unsigned long DHT_INTERVAL_MS = 2000;
static const unsigned long WIFI_TIMEOUT_MS = 20000;
static const unsigned long WIFI_RETRY_MS = 5000;
static const unsigned long SOCKET_RETRY_MS = 3000;
#if SERVE_WEB_INTERFACE
static const unsigned long PROXY_TIMEOUT_MS = 4000;
static const uint16_t WEB_PORT = 80;
#endif

// The claim indicator is deliberately nothing at all.
//
// The relays are the organs of the home: they switch whatever a person wired into
// them, and blinking one to say "the board is looking for an owner" would throw a
// heavy load on and off for no reason. The board says it needs an owner over its
// own serial line, and the interface of the account shows the offer, which is
// where a person looks for it anyway.
//
// The claim window reopens on its own while nobody has taken the board: a user often
// walks away from a box they just opened and only looks at the interface later.
// Once the board is owned it never reopens by itself.
static const unsigned long CLAIM_REOPEN_MS = 60000;

static char deviceKey[DEVICE_KEY_SIZE + 1];
static bool deviceClaimed = false;
static unsigned long claimUntilAt = 0;
static unsigned long reconnectAt = 0;

// The board is waiting for its owner to fill in the network.
static bool awaitingSetup = false;

WebSocketsClient socket;
DHT dht(DHT_PIN, DHT_TYPE);
Provisioning provisioning;
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
static unsigned long lastReconnectAt = 0;
static bool socketStarted = false;
static char frame[FRAME_SIZE];

// ---------------------------------------------------------------------------
// Identity of the board
//
// A board that has never been provisioned gets a key of its own on the first boot
// and keeps it in the flash of the chip. Nothing about it lives in the code, so
// the same binary is sold to everybody and nobody ever opens the IDE.
//
// The board asks for an owner only while it has one of two claims on it: it was
// just provisioned, or FLASH was held while the power went on. Holding FLASH pulls
// GPIO0 to ground, and GPIO0 is also relay 3 on this wiring, so the request is a
// gesture on the board rather than something a person has to type.
// ---------------------------------------------------------------------------

bool claiming() {
    return !deviceClaimed && claimUntilAt > 0 && millis() < claimUntilAt;
}

void openClaimWindow() {
    claimUntilAt = millis() + CLAIM_WINDOW_MS;
    Serial.printf("[claim] asking for an owner for %lu ms\n", (unsigned long)CLAIM_WINDOW_MS);
}

void markClaimed() {
    deviceClaimed = true;
    claimUntilAt = 0;
    configStoreSetClaimed(true);
    Serial.println("[claim] the board belongs to an account now");
}

/** Drop the stored ownership and start looking for an owner again.
 *
 * The flag in the flash is only a cache of what the server said last. When the
 * server says it does not know the board, the cache is wrong and has to go,
 * otherwise the board believes it is paired and never asks again.
 */
void forgetOwnership() {
    if (!deviceClaimed) {
        return;
    }
    deviceClaimed = false;
    configStoreSetClaimed(false);
    Serial.println("[claim] stored ownership was wrong, looking for an owner again");
}

void loadDeviceKey() {
    configStoreBegin();

    deviceClaimed = configStoreIsClaimed();
    size_t index = configStoreReadDeviceKey(deviceKey, sizeof(deviceKey));

    if (index == DEVICE_KEY_SIZE) {
        Serial.println("[id] key read from flash");
        return;
    }

    // First boot of this board: the key is derived from the chip itself and from
    // the moment of the boot, so two boards flashed with the same binary still
    // differ and nothing has to be provisioned at the factory.
    randomSeed(((uint32_t)ESP.getChipId() << 16) ^ micros());
    for (index = 0; index < DEVICE_KEY_SIZE; index++) {
        char digit = "0123456789abcdef"[random(0, 15)];
        deviceKey[index] = digit;
    }
    deviceKey[DEVICE_KEY_SIZE] = '\0';
    configStoreWriteDeviceKey(deviceKey);
    configStoreSetClaimed(false);
    Serial.println("[id] first boot, key generated and stored in flash");
}

/** Read the network of the board out of its own flash.
 *
 * A board that has never been set up has no network, and the caller puts it
 * into the setup mode instead of trying to reach a server.
 */
void loadNetwork() {
    configStoreLoadNetwork(network);
    if (!networkConfigIsValid(network)) {
        Serial.println("[wifi] no network yet, waiting for the owner to fill it in");
        return;
    }
    Serial.printf(
        "[wifi] network %s, server %s:%u\n",
        network.ssid,
        network.serverHost,
        network.socketPort
    );
}

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
    // Every field is needed and none is repeated: the frame has to fit into the
    // fixed buffer, and a truncated JSON object is a handshake the backend cannot
    // read, which looks exactly like a board that is not there.
    //
    // The network the board is on travels with the handshake, so the interface
    // shows where a board is without asking it anything.
    snprintf(
        frame,
        FRAME_SIZE,
        "{\"type\":\"HELLO\",\"firmware_version\":\"%s\",\"protocol_version\":%d,"
        "\"pairing_key\":\"%s\",\"label\":\"%06X\",\"claim\":%s,\"relays\":[%s],"
        "\"ssid\":\"%s\",\"provisioned\":%s}",
        FIRMWARE_VERSION,
        PROTOCOL_VERSION,
        deviceKey,
        ESP.getChipId(),
        claiming() ? "true" : "false",
        relays,
        network.ssid,
        network.provisioned ? "true" : "false"
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

/** Reopen the claim window while the board has no owner.
 *
 * Without this the board would ask exactly once and then stay silent forever, and
 * a user who opened the box and closed it again would never know that the board was
 * still waiting.
 */
void serviceClaimWindow() {
    if (deviceClaimed || claimUntilAt == 0) {
        return;
    }
    if ((int32_t)(millis() - claimUntilAt) < 0) {
        return;
    }
    openClaimWindow();
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

// ---------------------------------------------------------------------------
// Network of the board
//
// The backend owns the network of a board: the owner changes it in the
// interface, and the backend sends the new values over the socket. The board
// writes them into its own flash and reconnects, so the change survives a power
// cycle and nothing has to be typed into the board again.
// ---------------------------------------------------------------------------

void handleSetNetwork(const char *message) {
    NetworkConfig updated = network;

    char ssid[NETWORK_SSID_SIZE] = "";
    char password[NETWORK_PASSWORD_SIZE] = "";
    char host[NETWORK_HOST_SIZE] = "";
    char path[NETWORK_PATH_SIZE] = "";
    int serverPort = 0;
    int socketPort = 0;

    bool hasSsid = readStringField(message, "ssid", ssid, sizeof(ssid));
    bool hasHost = readStringField(message, "host", host, sizeof(host));
    readStringField(message, "password", password, sizeof(password));
    bool hasPath = readStringField(message, "socket_path", path, sizeof(path));
    bool hasServerPort = readIntField(message, "server_port", &serverPort);
    bool hasSocketPort = readIntField(message, "socket_port", &socketPort);

    if (!hasSsid || ssid[0] == '\0') {
        sendError("BAD_COMMAND", "missing network name");
        return;
    }
    if (hasHost && host[0] != '\0' && !networkHostIsNumeric(host)) {
        sendError("BAD_COMMAND", "the server address must be numeric");
        return;
    }

    strcpy(updated.ssid, ssid);
    strcpy(updated.password, password);
    if (hasHost && host[0] != '\0') {
        strcpy(updated.serverHost, host);
    }
    if (hasPath && path[0] != '\0') {
        strcpy(updated.socketPath, path);
    }
    if (hasServerPort && serverPort > 0) {
        updated.serverPort = (uint16_t)serverPort;
    }
    if (hasSocketPort && socketPort > 0) {
        updated.socketPort = (uint16_t)socketPort;
    }
    updated.provisioned = true;

    char commandId[32] = "";
    readStringField(message, "command_id", commandId, sizeof(commandId));

    network = updated;
    configStoreSaveNetwork(network);
    sendAck(commandId);
    Serial.printf(
        "[wifi] network changed to %s, server %s:%u\n",
        network.ssid,
        network.serverHost,
        network.socketPort
    );

    // The board lives on the new network from now on, so the radio has to leave
    // the old one and the socket has to come back on the new one. The join is
    // not waited for here: the loop notices the lost connection and joins the
    // network again, which is also where the address of the server is read from.
    WiFi.disconnect();
    socket.disconnect();
    socketStarted = false;
    lastReconnectAt = 0;
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
    if (strcmp(type, "CLAIM") == 0) {
        // The server does not know this board. Whatever the board remembered about
        // being owned was wrong, so the answer is dropped and the board asks
        // again: a stuck flag in the flash must not be able to silence a board
        // forever.
        Serial.println("[claim] server is holding this board for an account");
        forgetOwnership();
        openClaimWindow();
        // Dial in again in a few seconds: by then the account that pressed the
        // button in the interface is already stored and the board comes online.
        reconnectAt = millis() + CLAIM_RETRY_MS;
        socket.disconnect();
        return;
    }
    if (strcmp(type, "CLAIMED") == 0) {
        // The server resolved this key to an account, so the board is owned. The
        // answer is written to the flash, so the board never asks again even after
        // a power cycle, and the indicator stops blinking right away.
        markClaimed();
        return;
    }
    if (strcmp(type, "REJECTED") == 0) {
        char reason[32] = "";
        readStringField(message, "reason", reason, sizeof(reason));
        Serial.printf("[claim] server refused the board: %s\n", reason);
        deviceClaimed = false;
        claimUntilAt = 0;
        configStoreSetClaimed(false);
        return;
    }
    if (strcmp(type, "SET_NETWORK") == 0) {
        // The backend sends the network of the board when the owner changes it in
        // the interface. The values replace the ones in the flash, so the board
        // keeps them across a power cycle, and the board reconnects right away.
        handleSetNetwork(message);
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
    return out->fromString(String(network.serverHost));
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
    if (!client.connect(backend, (int)network.serverPort)) {
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
        network.serverHost,
        network.serverPort,
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
    if (!backend.fromString(String(network.serverHost))) {
        Serial.printf("[ws] the server address must be numeric, got %s\n", network.serverHost);
        socketStarted = true;
        return;
    }
    socket.begin(backend, network.socketPort, network.socketPath);
    socket.onEvent(onSocketEvent);
    socketStarted = true;
    lastSocketTryAt = millis();
    Serial.printf("[ws] connecting to %s:%u\n", network.serverHost, network.socketPort);
}

void maintainSocket() {
    if (WiFi.status() != WL_CONNECTED) {
        socketStarted = false;
        return;
    }
    unsigned long now = millis();
    if (reconnectAt != 0) {
        if (now < reconnectAt) {
            return;
        }
        // The board was told to dial in again after the announcement, so that the
        // very next handshake already resolves to the account that took it.
        reconnectAt = 0;
        socketStarted = false;
    }
    if (socketStarted) {
        return;
    }
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

/**
 * Join the network the board was told about.
 *
 * @param timeoutMs How long the board waits for the network.
 * @return True when the board is on the network.
 */
bool joinNetwork(unsigned long timeoutMs) {
    WiFi.mode(WIFI_STA);
    // The core keeps its own copy of the network in the flash, and the board
    // keeps the only copy that matters in its own. Two copies would wear the
    // flash twice and could disagree after a power cut.
    WiFi.persistent(false);

    Serial.print("[wifi] joining ");
    Serial.println(network.ssid);
    if (network.password[0] == '\0') {
        WiFi.begin(network.ssid);
    } else {
        WiFi.begin(network.ssid, network.password);
    }

    unsigned long startedAt = millis();
    while (WiFi.status() != WL_CONNECTED) {
        delay(250);
        Serial.print('.');
        if (millis() - startedAt > timeoutMs) {
            Serial.println();
            Serial.println("[wifi] timed out");
            return false;
        }
    }
    Serial.println();
    Serial.print("[wifi] connected, ip=");
    Serial.println(WiFi.localIP());
    return true;
}

/**
 * Start everything that only makes sense on a board that is on the network.
 *
 * @return None.
 */
void startService() {
    // FLASH is pulled to ground by the button, and GPIO0 is also relay 3 on this
    // wiring, so holding it while powering up is what asks for an owner right away.
    // The flag in the flash is only a cache of the last answer of the server: even a
    // board that believes it is paired asks again when the server tells it that the
    // key is unknown, which is why the window below is not the only way in.
    if (digitalRead(FLASH_BUTTON_PIN) == LOW) {
        forgetOwnership();
        openClaimWindow();
        Serial.println("[claim] FLASH held at boot, opening the claim window");
    } else if (deviceClaimed) {
        Serial.println("[claim] flash says this board is owned, waiting for the server");
    } else {
        openClaimWindow();
        Serial.println("[claim] never provisioned, opening the claim window");
    }

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

/**
 * Raise the access point and wait for the owner to fill in the network.
 *
 * @return None.
 */
void startProvisioning() {
    awaitingSetup = true;
    provisioning.begin();
}

void setup() {
    Serial.begin(115200);
    delay(200);
    Serial.println();
    Serial.println("[boot] smart home esp8266 firmware");
    Serial.printf("[boot] free heap %u\n", ESP.getFreeHeap());

    loadDeviceKey();
    loadNetwork();

    pinMode(FLASH_BUTTON_PIN, INPUT_PULLUP);

    for (uint8_t index = 0; index < RELAY_COUNT; index++) {
        pinMode(RELAY_PINS[index], OUTPUT);
        writeRelayPin(index, false);
    }

    dht.begin();

    if (!networkConfigIsValid(network)) {
        // The board was never set up, so it asks to be set up instead of trying to
        // reach a server it cannot know the address of.
        Serial.println("[wifi] no network, starting the setup access point");
        startProvisioning();
        return;
    }

    if (!joinNetwork(WIFI_TIMEOUT_MS)) {
        // The network is gone or the password was wrong. The only way forward is
        // to let the owner in again, so the access point goes up once more.
        Serial.println("[wifi] the network is unreachable, starting the setup access point");
        startProvisioning();
        return;
    }

    startService();
}

void loop() {
    if (awaitingSetup) {
        provisioning.loop();
        NetworkConfig submitted;
        if (provisioning.takeResult(submitted)) {
            network = submitted;
            provisioning.stop();
            awaitingSetup = false;
            if (joinNetwork(WIFI_TIMEOUT_MS)) {
                startService();
            } else {
                Serial.println("[wifi] the new network is unreachable, starting the setup access point");
                startProvisioning();
            }
        }
        return;
    }

    if (WiFi.status() != WL_CONNECTED) {
        // The radio is asked to try again once in a while, not on every pass of
        // the loop: the core queues the request and the second one would only
        // cost the board the time it needs for the first.
        //
        // The network is joined again by name rather than by reconnect, because
        // the board keeps its settings in its own flash and not in the one of
        // the core, which is told not to keep a copy of them.
        unsigned long now = millis();
        if (now - lastReconnectAt >= WIFI_RETRY_MS) {
            lastReconnectAt = now;
            Serial.println("[wifi] lost connection, joining the network again");
            socketStarted = false;
            joinNetwork(WIFI_TIMEOUT_MS);
        }
    }
#if SERVE_WEB_INTERFACE
    handleWeb();
#endif
    socket.loop();
    maintainSocket();
    sendTelemetry();
    serviceClaimWindow();
}

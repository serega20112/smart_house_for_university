/**
 * @file transport.cpp
 * @brief Дозвон до сервера, handshake и кадры состояния.
 *
 * Кадр строится документом ArduinoJson поверх фиксированного буфера: строка с
 * кавычкой или обратным слэшем (имя сети такое вполне может содержать) ломала бы
 * ручной snprintf-конструктор, а сериализатор экранирует её сам.
 */

#include "transport.h"

#include <ArduinoJson.h>
#include <ESP8266WiFi.h>
#include <WebSocketsClient.h>
#include <math.h>
#include <string.h>

#include "identity.h"
#include "radio.h"
#include "settings.h"

namespace {

/** Клиент сокета: одна плата — одно соединение. */
WebSocketsClient socket;

/** Поставщик состояния, которое кладётся в кадры. */
BoardStatusProvider statusProvider = nullptr;

/** Тот, кто разбирает команды сервера. */
BoardCommandHandler commandHandler = nullptr;

/** Общий буфер кадров: строит кадр тот, кто его и отправляет. */
char frame[FRAME_SIZE];

/** Момент прошлой телеметрии; ноль — ещё не отправляли. */
unsigned long lastTelemetryAt = 0;

/** Момент прошлой попытки дозвона; ноль — попыток ещё не было. */
unsigned long lastTryAt = 0;

/** Момент, до которого дозвоном не занимаются; ноль — можно звонить. */
unsigned long redialAt = 0;

/** Затребован ли дозвон после потери связи. */
bool dialRequested = false;

/**
 * @brief Спрашивает у поставщика, в каком состоянии плата сейчас.
 *
 * @param out Куда ложится состояние.
 */
void collectStatus(BoardStatus *out) {
    out->relayCount = 0;
    out->temperature = NAN;
    out->humidity = NAN;
    out->askingForOwner = false;
    if (statusProvider != nullptr) {
        statusProvider(out);
    }
}

/**
 * @brief Шлёт текст кадра, если соединение держится.
 *
 * @param text Готовый JSON кадра.
 */
void sendText(const char *text) {
    if (!socket.isConnected()) {
        return;
    }
    socket.sendTXT(text, strlen(text));
}

/**
 * @brief Превращает документ в кадр и отправляет его.
 *
 * Длина меряется до записи: обрезанный по буферу JSON сервер прочитал бы как
 * отсутствующий кадр, и выглядело бы это как плата, которая не дозвонилась.
 *
 * @param doc Документ с полями кадра.
 */
void sendDocument(JsonDocument &doc) {
    const size_t needed = measureJson(doc);
    if (needed == 0 || needed >= FRAME_SIZE) {
        Serial.printf("[ws] frame does not fit into %u bytes\n", static_cast<unsigned>(FRAME_SIZE));
        return;
    }
    serializeJson(doc, frame, FRAME_SIZE);
    sendText(frame);
}

/**
 * @brief Кладёт положения каналов в массив документа.
 *
 * @param doc Документ кадра.
 * @param status Состояние платы.
 */
void addRelays(JsonDocument &doc, const BoardStatus &status) {
    JsonArray relays = doc.createNestedArray("relays");
    for (uint8_t index = 0; index < status.relayCount; index++) {
        relays.add(status.relays[index]);
    }
}

/**
 * @brief Шлёт handshake: кто мы, какой у нас ключ и что сейчас у реле.
 *
 * Каждое поле нужно и ни одно не повторяется: handshake, который сервер не может
 * прочитать, — это плата, которая на него не звонилась.
 *
 * Сеть, в которой плата находится, идёт вместе с handshake, поэтому интерфейс
 * показывает, где плата, ни о чём её не спрашивая.
 */
void sendHello() {
    BoardStatus status;
    collectStatus(&status);
    char label[16];
    identityLabel(label, sizeof(label));
    const NetworkConfig &network = settingsCurrent();

    StaticJsonDocument<FRAME_SIZE> doc;
    doc["type"] = "HELLO";
    doc["firmware_version"] = FIRMWARE_VERSION;
    doc["protocol_version"] = PROTOCOL_VERSION;
    doc["pairing_key"] = identityKey();
    doc["label"] = label;
    doc["claim"] = status.askingForOwner;
    addRelays(doc, status);
    doc["ssid"] = network.ssid;
    doc["provisioned"] = network.provisioned;
    // Сервер, которому плата докладывает, едет рядом с ssid: интерфейс заполняет
    // адрес из того, что плата уже использует, а не спрашивает человека второй раз.
    // Пароль сети здесь не звучит никогда — это секрет, он остаётся в памяти платы.
    doc["server_host"] = network.serverHost;
    doc["server_port"] = network.serverPort;
    doc["socket_port"] = network.socketPort;
    doc["socket_path"] = network.socketPath;
    sendDocument(doc);
}

/**
 * @brief Шлёт периодические показания датчиков, не трогая реле.
 */
void sendSensorData() {
    BoardStatus status;
    collectStatus(&status);

    StaticJsonDocument<FRAME_SIZE> doc;
    doc["type"] = "SENSOR_DATA";
    doc["temperature"] = status.temperature;
    doc["humidity"] = status.humidity;
    sendDocument(doc);
}

/**
 * @brief Реагирует на события сокета.
 *
 * @param type Событие библиотеки.
 * @param payload Текст или байты, пришедшие с ним.
 * @param length Их длина.
 */
void onSocketEvent(WStype_t type, uint8_t *payload, size_t length) {
    (void)length;
    switch (type) {
        case WStype_CONNECTED:
            Serial.println("[ws] connected to backend");
            dialRequested = false;
            sendHello();
            transportSendState();
            break;
        case WStype_DISCONNECTED:
            Serial.println("[ws] disconnected");
            break;
        case WStype_TEXT:
            if (commandHandler != nullptr) {
                commandHandler(reinterpret_cast<const char *>(payload));
            }
            break;
        default:
            break;
    }
}

/**
 * @brief Затребованный платой дозвон: адрес сервера берётся из её настроек.
 */
void dial() {
    const NetworkConfig &network = settingsCurrent();
    IPAddress backend;
    if (!backend.fromString(network.serverHost)) {
        Serial.printf(
            "[ws] the server address must be numeric, got %s\n",
            network.serverHost
        );
        return;
    }
    socket.begin(backend, network.socketPort, network.socketPath);
    socket.onEvent(onSocketEvent);
    lastTryAt = millis();
    Serial.printf("[ws] connecting to %s:%u\n", network.serverHost, network.socketPort);
}

}  // namespace

void transportBegin(BoardStatusProvider status, BoardCommandHandler onCommand) {
    statusProvider = status;
    commandHandler = onCommand;
    dialRequested = true;
}

void transportLoop() {
    socket.loop();

    if (!radioLinked()) {
        dialRequested = true;
        return;
    }
    unsigned long now = millis();
    if (redialAt != 0) {
        if (now < redialAt) {
            return;
        }
        // Плате сказали объявить себя серверу заново: к следующему handshake аккаунт,
        // который её забрал, уже сохранён, и плата приходит сразу к нему.
        redialAt = 0;
        dialRequested = true;
    }
    // Соединение уже держится — в этом цикле делать нечего. Раньше сюда попадали и с
    // открытым сокетом, и каждый цикл звали dial(), который перетыкал socket.begin():
    // плата рвала и открывала соединение десятки раз в секунду.
    if (socket.isConnected()) {
        return;
    }
    if (!dialRequested && lastTryAt != 0 && now - lastTryAt < SOCKET_RETRY_MS) {
        return;
    }
    dialRequested = false;
    dial();
}

bool transportConnected() {
    return socket.isConnected();
}

void transportSendState() {
    BoardStatus status;
    collectStatus(&status);

    StaticJsonDocument<FRAME_SIZE> doc;
    doc["type"] = "STATE";
    addRelays(doc, status);
    if (!isnan(status.temperature)) {
        doc["temperature"] = status.temperature;
    }
    if (!isnan(status.humidity)) {
        doc["humidity"] = status.humidity;
    }
    sendDocument(doc);
}

void transportSendTelemetry() {
    unsigned long now = millis();
    if (lastTelemetryAt != 0 && now - lastTelemetryAt < TELEMETRY_INTERVAL_MS) {
        return;
    }
    lastTelemetryAt = now;

    BoardStatus status;
    collectStatus(&status);
    if (isnan(status.temperature) || isnan(status.humidity)) {
        Serial.println("[dht] no valid reading, check wiring of D7");
        return;
    }
    Serial.printf(
        "[dht] %.1f C %.1f %%\n",
        status.temperature,
        status.humidity
    );
    sendSensorData();
}

void transportSendAck(const char *commandId) {
    StaticJsonDocument<FRAME_SIZE> doc;
    doc["type"] = "ACK";
    doc["command_id"] = commandId;
    sendDocument(doc);
}

void transportSendError(const char *code, const char *message) {
    StaticJsonDocument<FRAME_SIZE> doc;
    doc["type"] = "ERROR";
    doc["code"] = code;
    doc["message"] = message;
    sendDocument(doc);
}

void transportRedial(unsigned long retryAfterMs) {
    socket.disconnect();
    redialAt = millis() + retryAfterMs;
}

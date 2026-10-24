/**
 * @file commands.cpp
 * @brief Разбор кадров сервера.
 *
 * Кадр читает ArduinoJson: пробелы и переводы строк между ключом и значением JSON не
 * запрещает, и экранированная кавычка внутри строки — тоже не редкость, а ручной
 * strstr-разбор на этом спотыкался. Документ при разборе только читается и никак не
 * меняется: команда не может переписать сама себя на лету.
 */

#include "commands.h"

#include <ArduinoJson.h>
#include <string.h>

#include "claim.h"
#include "identity.h"
#include "radio.h"
#include "relay.h"
#include "sensors.h"
#include "settings.h"
#include "transport.h"

namespace {

/** Через сколько плата звонится снова, если сервер держит её для аккаунта. */
const unsigned long CLAIM_RETRY_MS = 5000;

/**
 * @brief Читает текст поля, возвращая пустую строку, если поля нет.
 *
 * @param doc Документ кадра.
 * @param key Имя поля.
 * @return Значение поля текстом или пустая строка.
 */
const char *textOf(JsonDocument &doc, const char *key) {
    return doc[key] | "";
}

/**
 * @brief Замыкает или размыкает канал по кадру SET_RELAY.
 *
 * @param doc Документ кадра.
 */
void handleSetRelay(JsonDocument &doc) {
    if (!doc["channel"].is<int>() || !doc["state"].is<bool>()) {
        transportSendError("BAD_COMMAND", "missing channel or state");
        return;
    }
    const int channel = doc["channel"];
    if (channel < 1 || channel > RELAY_COUNT) {
        transportSendError("BAD_CHANNEL", "channel out of range 1..6");
        return;
    }

    relaySet(static_cast<uint8_t>(channel), static_cast<bool>(doc["state"]));
    transportSendAck(textOf(doc, "command_id"));
    transportSendState();
}

/**
 * @brief Меняет сеть платы по кадру SET_NETWORK.
 *
 * Значения ложатся во флеш самой платы, поэтому переживают перезапуск питания, и
 * плата переподключается сразу: следующий handshake придёт уже на новый адрес.
 * Присоединение здесь не ожидается: главный цикл сам заметит потерю связи и
 * приведёт сеть заново, откуда читается и адрес сервера.
 *
 * @param doc Документ кадра.
 */
void handleSetNetwork(JsonDocument &doc) {
    NetworkConfig updated = settingsCurrent();

    const char *ssid = textOf(doc, "ssid");
    const char *password = textOf(doc, "password");
    const char *host = textOf(doc, "host");
    const char *path = textOf(doc, "socket_path");
    const bool hasHost = host[0] != '\0';
    const bool hasPath = path[0] != '\0';
    const bool hasServerPort = doc["server_port"].is<int>();
    const bool hasSocketPort = doc["socket_port"].is<int>();
    const int serverPort = hasServerPort ? static_cast<int>(doc["server_port"]) : 0;
    const int socketPort = hasSocketPort ? static_cast<int>(doc["socket_port"]) : 0;

    if (ssid[0] == '\0') {
        transportSendError("BAD_COMMAND", "missing network name");
        return;
    }
    if (hasHost && !networkHostIsNumeric(host)) {
        transportSendError("BAD_COMMAND", "the server address must be numeric");
        return;
    }

    snprintf(updated.ssid, sizeof(updated.ssid), "%s", ssid);
    snprintf(updated.password, sizeof(updated.password), "%s", password);
    if (hasHost) {
        snprintf(updated.serverHost, sizeof(updated.serverHost), "%s", host);
    }
    if (hasPath) {
        snprintf(updated.socketPath, sizeof(updated.socketPath), "%s", path);
    }
    if (hasServerPort && serverPort > 0) {
        updated.serverPort = static_cast<uint16_t>(serverPort);
    }
    if (hasSocketPort && socketPort > 0) {
        updated.socketPort = static_cast<uint16_t>(socketPort);
    }
    updated.provisioned = true;

    const char *commandId = textOf(doc, "command_id");

    settingsSave(updated);
    transportSendAck(commandId);
    Serial.printf(
        "[wifi] network changed to %s, server %s:%u\n",
        updated.ssid,
        updated.serverHost,
        updated.socketPort
    );

    radioLeave();
    transportRedial(0);
}

/**
 * @brief Сервер не знает эту плату: владение было ошибочным, ищем хозяина заново.
 *
 * Флаг во флеше — только кеш последнего ответа сервера, поэтому залипший флаг не
 * должен иметь возможности заглушить плату навсегда.
 */
void handleClaim() {
    Serial.println("[claim] server is holding this board for an account");
    identityForgetOwner();
    claimOpen();
    transportRedial(CLAIM_RETRY_MS);
}

/**
 * @brief Сервер признал ключ: плата принадлежит аккаунту.
 *
 * Ответ пишется во флеш, поэтому плата больше не просит даже после перезапуска
 * питания.
 */
void handleClaimed() {
    identityMarkOwned();
    claimClose();
}

/**
 * @brief Сервер отверг плату: она снова ничья и будет просить хозяина.
 *
 * @param doc Документ кадра.
 */
void handleRejected(JsonDocument &doc) {
    Serial.printf("[claim] server refused the board: %s\n", textOf(doc, "reason"));
    identityForgetOwner();
    claimClose();
}

}  // namespace

void commandsHandle(const char *json) {
    StaticJsonDocument<512> doc;
    DeserializationError error = deserializeJson(doc, json);
    if (error) {
        transportSendError("BAD_MESSAGE", "frame is not valid JSON");
        return;
    }
    const char *type = textOf(doc, "type");
    if (strcmp(type, "SET_RELAY") == 0) {
        handleSetRelay(doc);
        return;
    }
    if (strcmp(type, "GET_STATE") == 0) {
        sensorsRead();
        transportSendState();
        return;
    }
    if (strcmp(type, "CLAIM") == 0) {
        handleClaim();
        return;
    }
    if (strcmp(type, "CLAIMED") == 0) {
        handleClaimed();
        return;
    }
    if (strcmp(type, "REJECTED") == 0) {
        handleRejected(doc);
        return;
    }
    if (strcmp(type, "SET_NETWORK") == 0) {
        handleSetNetwork(doc);
        return;
    }
    transportSendError("UNKNOWN_TYPE", "unsupported message type");
}

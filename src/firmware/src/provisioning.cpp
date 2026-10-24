/**
 * @file provisioning.cpp
 * @brief Точка доступа, которую плата поднимает, пока ей не сказали, куда идти.
 */

#include "provisioning.h"

#include <ESP8266WiFi.h>
#include <string.h>

#include "config_store.h"
#include "setup_page.h"

namespace {

/** Начало имени точки доступа. */
static const char ACCESS_POINT_PREFIX[] = "SmartHome-Setup-";

/**
 * @brief Строит имя точки доступа из идентификатора чипа.
 *
 * Идентификатор напечатан на плате, поэтому имя говорит человеку, какая из двух
 * плат в комнате требует настройки.
 *
 * @param out Буфер, куда записывается имя.
 * @param capacity Размер этого буфера.
 */
void buildAccessPointName(char *out, size_t capacity) {
    snprintf(out, capacity, "%s%06X", ACCESS_POINT_PREFIX, ESP.getChipId());
}

/**
 * @brief Пробел ли этот знак (включая переводы строк формы)?
 *
 * @param symbol Знак, пришедший из поля формы.
 * @return True для пробела, табуляции и любого перевода строки.
 */
bool isBlank(char symbol) {
    return symbol == ' ' || symbol == '\t' || symbol == '\r' || symbol == '\n';
}

}  // namespace

void Provisioning::begin() {
    char name[ACCESS_POINT_NAME_SIZE];
    buildAccessPointName(name, sizeof(name));

    WiFi.mode(WIFI_AP);
    WiFi.softAP(name);

    _server = std::make_unique<ESP8266WebServer>(SETUP_PORT);
    _server->on("/", HTTP_GET, [this]() { servePage(); });
    _server->on("/setup", HTTP_POST, [this]() { handleSubmit(); });
    _server->onNotFound([this]() { servePage(); });
    _server->begin();

    _active = true;
    Serial.printf("[setup] access point %s is up, open http://192.168.4.1/\n", name);
}

void Provisioning::loop() {
    if (!_active || _server == nullptr) {
        return;
    }
    _server->handleClient();
}

void Provisioning::stop() {
    if (!_active) {
        return;
    }
    if (_server != nullptr) {
        _server->stop();
        _server.reset();
    }
    WiFi.softAPdisconnect(true);
    _active = false;
    Serial.println("[setup] access point is down");
}

bool Provisioning::takeResult(NetworkConfig &out) {
    if (!_submitted) {
        return false;
    }
    out = _result;
    _submitted = false;
    return true;
}

void Provisioning::servePage() {
    _server->sendHeader("Cache-Control", "no-store");
    _server->send_P(200, "text/html; charset=utf-8", SETUP_PAGE);
}

void Provisioning::handleSubmit() {
    NetworkConfig config{};
    readField("ssid", config.ssid, sizeof(config.ssid));
    readField("password", config.password, sizeof(config.password));
    readField("host", config.serverHost, sizeof(config.serverHost));
    readField("socket_path", config.socketPath, sizeof(config.socketPath));
    config.serverPort = readNumber("server_port", DEFAULT_SERVER_PORT);
    config.socketPort = readNumber("socket_port", DEFAULT_SOCKET_PORT);
    config.provisioned = true;

    if (config.ssid[0] == '\0' || !networkHostIsNumeric(config.serverHost)) {
        Serial.println(
            "[setup] the form was refused, a network name and a numeric address are needed"
        );
        servePage();
        return;
    }

    if (config.socketPath[0] != '/') {
        strcpy(config.socketPath, DEFAULT_SOCKET_PATH);
    }

    configStoreSaveNetwork(config);
    _result = config;
    _submitted = true;

    Serial.printf(
        "[setup] saved network %s, server %s:%u\n",
        config.ssid,
        config.serverHost,
        config.socketPort
    );
    _server->sendHeader("Cache-Control", "no-store");
    _server->send_P(200, "text/html; charset=utf-8", SETUP_DONE_PAGE);
}

size_t Provisioning::readField(const char *name, char *out, size_t capacity) {
    out[0] = '\0';
    if (!_server->hasArg(name)) {
        return 0;
    }
    // Значение читается по ссылке и копируется в фиксированный буфер: собственная
    // String осталась бы в куче, а от оставленного ею фрагментирования эта микросхема
    // и погибает (Exception 29, LoadStoreError).
    //
    // Из текста убираются только ведущие и хвостовые пробелы. Имя сети «My Sweet
    // Home» и пароль «password 123» пробелы содержат, и вырезание их из середины
    // записало бы в память другую сеть: плата не смогла бы к ней подключиться и
    // ушла бы в вечный возврат к странице настройки.
    const String &value = _server->arg(name);
    size_t first = 0;
    size_t last = value.length();
    while (first < last && isBlank(value[first])) {
        first++;
    }
    while (last > first && isBlank(value[last - 1])) {
        last--;
    }
    size_t written = 0;
    for (size_t index = first; index < last && written + 1 < capacity; index++) {
        out[written++] = value[index];
    }
    out[written] = '\0';
    return written;
}

uint16_t Provisioning::readNumber(const char *name, uint16_t fallback) {
    if (!_server->hasArg(name)) {
        return fallback;
    }
    const String &value = _server->arg(name);
    long parsed = 0;
    size_t digits = 0;
    for (size_t index = 0; index < value.length(); index++) {
        char symbol = value[index];
        if (symbol < '0' || symbol > '9') {
            break;
        }
        parsed = parsed * 10 + (symbol - '0');
        digits++;
        if (parsed > 65535) {
            return fallback;
        }
    }
    if (digits == 0 || parsed == 0) {
        return fallback;
    }
    return static_cast<uint16_t>(parsed);
}

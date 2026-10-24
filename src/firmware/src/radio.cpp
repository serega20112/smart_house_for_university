/**
 * @file radio.cpp
 * @brief Присоединение к сети и попытка вернуться в неё.
 */

#include "radio.h"

#include <ESP8266WiFi.h>

#include "settings.h"

namespace {

/** Момент прошлой попытки вернуться в сеть; ноль — попыток ещё не было. */
unsigned long lastAttemptAt = 0;

}  // namespace

bool radioJoin(unsigned long timeoutMs) {
    const NetworkConfig &network = settingsCurrent();

    WiFi.mode(WIFI_STA);
    // Ядру сказано ничего не сохранять: единственная копия настроек лежит во флеше
    // самой платы, иначе после пропадания питания они могли бы разойтись.
    WiFi.persistent(false);
    // Энергосбережение модема выключено намеренно: спящий радиомодуль ESP8266 рвёт
    // ассоциацию с точкой доступа, а вместе с ней и держаемый WebSocket — дом виделся
    // то «на связи», то «недоступен». Плата питается от сети, экономить ей нечего.
    WiFi.setSleep(WIFI_NONE_SLEEP);

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
    lastAttemptAt = millis();
    return true;
}

bool radioLinked() {
    return WiFi.status() == WL_CONNECTED;
}

bool radioKeepAlive() {
    if (radioLinked()) {
        return true;
    }
    unsigned long now = millis();
    if (lastAttemptAt != 0 && now - lastAttemptAt < RADIO_RETRY_MS) {
        return false;
    }
    lastAttemptAt = now;
    Serial.println("[wifi] lost connection, joining the network again");
    return radioJoin(RADIO_JOIN_TIMEOUT_MS);
}

void radioLeave() {
    WiFi.disconnect();
    lastAttemptAt = 0;
}

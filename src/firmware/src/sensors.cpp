/**
 * @file sensors.cpp
 * @brief Чтение DHT22 и последние полученные значения.
 */

#include "sensors.h"

#include <DHT.h>
#include <math.h>

namespace {

/** Пин, к которому подключён вывод DATA датчика: D7. */
const uint8_t DHT_PIN = 13;

/** Тип датчика, с которым работает библиотека. */
const uint8_t DHT_TYPE = DHT22;

/** Минимальный интервал между двумя чтениями датчика. */
const unsigned long DHT_INTERVAL_MS = 2000;

/** Датчик, разделяемый всеми, кто просит показания. */
DHT dht(DHT_PIN, DHT_TYPE);

/** Момент прошлого чтения; ноль — «ещё не читали». */
unsigned long lastReadAt = 0;

/** Последние валидные показания; NaN означает, что датчик молчит. */
float temperature = NAN;
float humidity = NAN;

}  // namespace

void sensorsBegin() {
    dht.begin();
}

void sensorsRead() {
    unsigned long now = millis();
    if (lastReadAt != 0 && now - lastReadAt < DHT_INTERVAL_MS) {
        return;
    }
    lastReadAt = now;

    float currentTemperature = dht.readTemperature();
    float currentHumidity = dht.readHumidity();
    if (isnan(currentTemperature) || isnan(currentHumidity)) {
        return;
    }
    temperature = currentTemperature;
    humidity = currentHumidity;
}

bool sensorsReady() {
    return !isnan(temperature) && !isnan(humidity);
}

float sensorsTemperature() {
    return temperature;
}

float sensorsHumidity() {
    return humidity;
}

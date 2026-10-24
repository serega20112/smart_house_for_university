/**
 * @file relay.cpp
 * @brief Пины реле и их положения.
 */

#include "relay.h"

namespace {

/** Пины каналов в порядке нумерации: D1, D2, D3, D4, D5, D6. */
const uint8_t RELAY_PINS[RELAY_COUNT] = {5, 4, 0, 2, 14, 12};

/** Модули реле замыкаются низким уровнем. */
const bool RELAY_ACTIVE_LOW = true;

/** Кнопка FLASH есть на каждой плате ESP8266. Здесь на этом пине висит и реле 3,
 *  поэтому зажатая при подаче питания кнопка коротко замыкает этот контакт. */
const uint8_t FLASH_BUTTON_PIN = 0;

/** Положения контактов, как их помнит плата. */
bool relayOn[RELAY_COUNT] = {false, false, false, false, false, false};

/** Была ли кнопка FLASH зажата при старте; пин после этого становится выходом. */
bool flashHeldAtBoot = false;

/**
 * @brief Кладёт на пин уровень, соответствующий нужному положению контакта.
 *
 * @param index Номер канала с нуля.
 * @param on True для замкнутого контакта.
 */
void writeRelayPin(uint8_t index, bool on) {
    digitalWrite(RELAY_PINS[index], RELAY_ACTIVE_LOW ? !on : on);
}

}  // namespace

void relaysBegin() {
    pinMode(FLASH_BUTTON_PIN, INPUT_PULLUP);
    flashHeldAtBoot = digitalRead(FLASH_BUTTON_PIN) == LOW;
    for (uint8_t index = 0; index < RELAY_COUNT; index++) {
        pinMode(RELAY_PINS[index], OUTPUT);
        writeRelayPin(index, false);
        relayOn[index] = false;
    }
}

bool relaysFlashHeld() {
    return flashHeldAtBoot;
}

void relaySet(uint8_t channel, bool on) {
    if (channel < 1 || channel > RELAY_COUNT) {
        return;
    }
    relayOn[channel - 1] = on;
    writeRelayPin(channel - 1, on);
    Serial.printf("[relay] channel %u -> %s\n", channel, on ? "ON" : "OFF");
}

bool relayIsOn(uint8_t channel) {
    if (channel < 1 || channel > RELAY_COUNT) {
        return false;
    }
    return relayOn[channel - 1];
}

void relaysSnapshot(bool *out, size_t capacity) {
    if (out == nullptr || capacity == 0) {
        return;
    }
    for (size_t index = 0; index < capacity; index++) {
        out[index] = index < RELAY_COUNT ? relayOn[index] : false;
    }
}

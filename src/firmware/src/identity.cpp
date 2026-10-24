/**
 * @file identity.cpp
 * @brief Ключ платы и признак того, что у неё есть владелец.
 */

#include "identity.h"

#include "config_store.h"

namespace {

/** Ключ, который плата предъявляет серверу. */
char deviceKey[DEVICE_KEY_SIZE + 1];

/** Признак владельца — кеш последнего ответа сервера. */
bool deviceClaimed = false;

}  // namespace

void identityBegin() {
    configStoreBegin();

    deviceClaimed = configStoreIsClaimed();
    size_t index = configStoreReadDeviceKey(deviceKey, sizeof(deviceKey));

    if (index == DEVICE_KEY_SIZE) {
        Serial.println("[id] key read from flash");
        return;
    }

    // Первый запуск этой платы: ключ выводится из самого чипа и из момента запуска,
    // поэтому две платы, прошитые одной сборкой, всё равно разные, и на заводе
    // никому ничего не надо вписывать.
    randomSeed((static_cast<uint32_t>(ESP.getChipId()) << 16) ^ micros());
    for (index = 0; index < DEVICE_KEY_SIZE; index++) {
        deviceKey[index] = "0123456789abcdef"[random(0, 15)];
    }
    deviceKey[DEVICE_KEY_SIZE] = '\0';
    configStoreWriteDeviceKey(deviceKey);
    configStoreSetClaimed(false);
    Serial.println("[id] first boot, key generated and stored in flash");
}

const char *identityKey() {
    return deviceKey;
}

void identityLabel(char *out, size_t capacity) {
    snprintf(out, capacity, "%06X", ESP.getChipId());
}

bool identityHasOwner() {
    return deviceClaimed;
}

void identityMarkOwned() {
    deviceClaimed = true;
    configStoreSetClaimed(true);
    Serial.println("[claim] the board belongs to an account now");
}

void identityForgetOwner() {
    if (!deviceClaimed) {
        return;
    }
    deviceClaimed = false;
    configStoreSetClaimed(false);
    Serial.println("[claim] stored ownership was wrong, looking for an owner again");
}

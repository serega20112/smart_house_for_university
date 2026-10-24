/**
 * @file settings.cpp
 * @brief Действующие настройки сети платы.
 */

#include "settings.h"

#include "config_store.h"

namespace {

/** Значения, которыми плата пользуется прямо сейчас. */
NetworkConfig current{};

}  // namespace

bool settingsLoad() {
    configStoreLoadNetwork(current);
    if (!networkConfigIsValid(current)) {
        Serial.println("[wifi] no network yet, waiting for the owner to fill it in");
        return false;
    }
    Serial.printf(
        "[wifi] network %s, server %s:%u\n",
        current.ssid,
        current.serverHost,
        current.socketPort
    );
    return true;
}

const NetworkConfig &settingsCurrent() {
    return current;
}

void settingsSave(const NetworkConfig &config) {
    current = config;
    configStoreSaveNetwork(current);
}

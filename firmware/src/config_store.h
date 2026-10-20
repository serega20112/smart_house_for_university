/**
 * @file config_store.h
 * @brief The flash of the board as the only place its own settings live.
 *
 * Three things are kept in the flash of the chip: the key the board presents to
 * the server, the fact that it already has an owner, and the network it belongs
 * to. Nothing of this is compiled into the firmware, which is what lets one
 * binary serve every board.
 *
 * The layout is fixed and never moves, because a board that was already set up
 * has to find its own settings again after a reflash of the code.
 */

#pragma once

#include <Arduino.h>

#include "network_config.h"

/** Size of the emulated flash the settings are kept in. */
static const size_t EEPROM_SIZE = 256;

/** Offset of the key the board presents to the server. */
static const size_t DEVICE_KEY_OFFSET = 0;

/** Length of the key the board presents to the server. */
static const size_t DEVICE_KEY_SIZE = 32;

/** Offset of the flag telling whether the board already has an owner. */
static const size_t CLAIMED_FLAG_OFFSET = DEVICE_KEY_OFFSET + DEVICE_KEY_SIZE;

/** Offset of the block holding the network of the board. */
static const size_t NETWORK_OFFSET = CLAIMED_FLAG_OFFSET + 8;

/**
 * @brief Open the flash the settings are kept in.
 *
 * Calling it twice is harmless, so every entry point may call it.
 *
 * @return None.
 */
void configStoreBegin();

/**
 * @brief Read the key the board presents to the server.
 *
 * @param out Buffer the key is copied into.
 * @param capacity Size of that buffer.
 * @return The number of characters read, zero when the board has no key yet.
 */
size_t configStoreReadDeviceKey(char *out, size_t capacity);

/**
 * @brief Write the key the board presents to the server.
 *
 * @param key Key to store.
 * @return None.
 */
void configStoreWriteDeviceKey(const char *key);

/**
 * @brief Report whether the board already has an owner.
 *
 * @return True when the board belongs to an account.
 */
bool configStoreIsClaimed();

/**
 * @brief Record whether the board has an owner.
 *
 * @param claimed True when the board belongs to an account.
 * @return None.
 */
void configStoreSetClaimed(bool claimed);

/**
 * @brief Read the network of the board.
 *
 * @param out Configuration the stored values are written into.
 * @return True when the board was set up before.
 */
bool configStoreLoadNetwork(NetworkConfig &out);

/**
 * @brief Write the network of the board.
 *
 * @param config Configuration to store.
 * @return None.
 */
void configStoreSaveNetwork(const NetworkConfig &config);

/**
 * @file claim.cpp
 * @brief Состояние окна просьбы о хозяине.
 */

#include "claim.h"

#include "identity.h"

namespace {

/** Как долго плата просит себе хозяина за один раз. */
const uint32_t CLAIM_WINDOW_MS = 120000;

/** Момент, до которого окно открыто; ноль — окно никогда не открывалось. */
unsigned long claimUntilAt = 0;

}  // namespace

void claimOpen() {
    claimUntilAt = millis() + CLAIM_WINDOW_MS;
    Serial.printf(
        "[claim] asking for an owner for %lu ms\n",
        static_cast<unsigned long>(CLAIM_WINDOW_MS)
    );
}

void claimClose() {
    claimUntilAt = 0;
}

bool claimWindowOpen() {
    return !identityHasOwner() && claimUntilAt > 0 && millis() < claimUntilAt;
}

void claimService() {
    if (identityHasOwner() || claimUntilAt == 0) {
        return;
    }
    // Сравнение со знаком: millis() переполняется, и окно, открытое до переполнения,
    // должно закрыться и после него, а не пережить его на сорок шесть дней.
    if (static_cast<int32_t>(millis() - claimUntilAt) < 0) {
        return;
    }
    claimOpen();
}

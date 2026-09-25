"""Fixed code emitted into gen/ (E2E library for C and Python).

E2E profile (ARCHITECTURE section 4, D-005, AUTOSAR Profile 1/2-like):
  byte 0          CRC8 SAE J1850 (poly 0x1D, init 0xFF, final XOR 0xFF) computed over
                  DataID low byte, DataID high byte, then frame bytes 1..len-1.
                  The DataID is never transmitted.
  byte 1 bits 0-3 alive counter 0..15, +1 per transmitted frame.
Receiver: CRC, counter (repeat = frozen, jump > 1 = lost/out-of-order) and timeout
(3 x cycle). The first frame after init only arms the counter (INITIAL, not OK), so a
single stale or replayed frame can never be accepted as valid on its own. The same
re-arming happens when a frame arrives after the timeout: a 4-bit counter wraps after
16 lost frames, so without it a long outage could look like a +1 step.
"""

E2E_H = r"""#ifndef MOTO_E2E_H
#define MOTO_E2E_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define MOTO_E2E_CRC_BYTE (0u)
#define MOTO_E2E_COUNTER_BYTE (1u)
#define MOTO_E2E_COUNTER_MASK (0x0Fu)
#define MOTO_E2E_MAX_DELTA_COUNTER (1u)
#define MOTO_E2E_MIN_LENGTH (2u)
#define MOTO_E2E_MAX_LENGTH (8u) /* classic CAN */

typedef enum {
    MOTO_E2E_OK = 0,         /* CRC valid, counter +1, within the timeout: data usable */
    MOTO_E2E_INITIAL,        /* first valid frame after init or after a timeout: not usable yet */
    MOTO_E2E_BAD_LENGTH,     /* length outside 2..8 or NULL arguments */
    MOTO_E2E_CRC_ERROR,      /* CRC mismatch: frame corrupted or wrong DataID */
    MOTO_E2E_REPEATED,       /* counter did not change: sender frozen or frame repeated */
    MOTO_E2E_WRONG_SEQUENCE, /* counter jumped: frames lost or reordered */
    MOTO_E2E_TIMEOUT         /* no OK frame within the timeout */
} moto_e2e_status_t;

typedef struct {
    uint8_t counter;
} moto_e2e_tx_state_t;

/* Receiver state. Use it from one execution context only (check and check_timeout
 * must not race, e.g. between a CAN ISR and the main loop). */
typedef struct {
    uint32_t timeout_ms; /* <MSG>_E2E_TIMEOUT_MS from platform_meta.h */
    uint32_t ref_ms;     /* time of the last OK frame, or of arming if none yet */
    uint8_t last_counter;
    uint8_t armed;  /* 0 until a CRC-valid frame arms the counter */
    uint8_t has_ok; /* 0 until the first OK frame since arming */
} moto_e2e_rx_state_t;

void moto_e2e_tx_init(moto_e2e_tx_state_t *tx);
void moto_e2e_rx_init(moto_e2e_rx_state_t *rx, uint32_t timeout_ms);

/* CRC over DataID (low, high) and data[1..len-1]. */
uint8_t moto_e2e_crc8(uint16_t data_id, const uint8_t *data, uint8_t len);

/* Writes the alive counter into byte 1 bits 0-3 (bits 4-7 are kept), then the CRC into
 * byte 0, then advances the counter. Call once per frame, after packing the payload and
 * only when the frame is actually queued for sending (a skipped frame shows up as
 * WRONG_SEQUENCE at the receiver). */
moto_e2e_status_t moto_e2e_protect(uint16_t data_id, uint8_t *data, uint8_t len,
                                   moto_e2e_tx_state_t *tx);

/* Checks one received frame. Only MOTO_E2E_OK means the payload may be used. */
moto_e2e_status_t moto_e2e_check(uint16_t data_id, const uint8_t *data, uint8_t len,
                                 moto_e2e_rx_state_t *rx, uint32_t now_ms);

/* Periodic check: MOTO_E2E_TIMEOUT if no OK frame arrived within rx->timeout_ms.
 * Wrap-around safe. */
moto_e2e_status_t moto_e2e_check_timeout(const moto_e2e_rx_state_t *rx, uint32_t now_ms);

#ifdef __cplusplus
}
#endif

#endif /* MOTO_E2E_H */
"""

E2E_C = r"""#include "moto_e2e.h"

#include <stddef.h>

#define MOTO_E2E_CRC8_POLY (0x1Du)
#define MOTO_E2E_CRC8_INIT (0xFFu)
#define MOTO_E2E_CRC8_XOR_OUT (0xFFu)

static uint8_t crc8_update(uint8_t crc, uint8_t byte)
{
    uint8_t bit;
    uint8_t c = (uint8_t)(crc ^ byte);
    for (bit = 0u; bit < 8u; bit++) {
        if ((c & 0x80u) != 0u) {
            c = (uint8_t)((uint8_t)(c << 1) ^ MOTO_E2E_CRC8_POLY);
        } else {
            c = (uint8_t)(c << 1);
        }
    }
    return c;
}

static int length_ok(uint8_t len)
{
    return (len >= MOTO_E2E_MIN_LENGTH) && (len <= MOTO_E2E_MAX_LENGTH);
}

void moto_e2e_tx_init(moto_e2e_tx_state_t *tx)
{
    if (tx != NULL) {
        tx->counter = 0u;
    }
}

void moto_e2e_rx_init(moto_e2e_rx_state_t *rx, uint32_t timeout_ms)
{
    if (rx != NULL) {
        rx->timeout_ms = timeout_ms;
        rx->ref_ms = 0u;
        rx->last_counter = 0u;
        rx->armed = 0u;
        rx->has_ok = 0u;
    }
}

uint8_t moto_e2e_crc8(uint16_t data_id, const uint8_t *data, uint8_t len)
{
    uint8_t crc = MOTO_E2E_CRC8_INIT;
    uint8_t i;
    crc = crc8_update(crc, (uint8_t)(data_id & 0xFFu));
    crc = crc8_update(crc, (uint8_t)((data_id >> 8) & 0xFFu));
    if (data != NULL) {
        for (i = 1u; i < len; i++) {
            crc = crc8_update(crc, data[i]);
        }
    }
    return (uint8_t)(crc ^ MOTO_E2E_CRC8_XOR_OUT);
}

moto_e2e_status_t moto_e2e_protect(uint16_t data_id, uint8_t *data, uint8_t len,
                                   moto_e2e_tx_state_t *tx)
{
    moto_e2e_status_t status = MOTO_E2E_BAD_LENGTH;
    if ((data != NULL) && (tx != NULL) && length_ok(len)) {
        data[MOTO_E2E_COUNTER_BYTE] = (uint8_t)((data[MOTO_E2E_COUNTER_BYTE] & 0xF0u) |
                                                (tx->counter & MOTO_E2E_COUNTER_MASK));
        data[MOTO_E2E_CRC_BYTE] = moto_e2e_crc8(data_id, data, len);
        tx->counter = (uint8_t)((tx->counter + 1u) & MOTO_E2E_COUNTER_MASK);
        status = MOTO_E2E_OK;
    }
    return status;
}

moto_e2e_status_t moto_e2e_check(uint16_t data_id, const uint8_t *data, uint8_t len,
                                 moto_e2e_rx_state_t *rx, uint32_t now_ms)
{
    moto_e2e_status_t status;
    uint8_t counter;
    uint8_t delta;

    if ((data == NULL) || (rx == NULL) || (length_ok(len) == 0)) {
        status = MOTO_E2E_BAD_LENGTH;
    } else if (moto_e2e_crc8(data_id, data, len) != data[MOTO_E2E_CRC_BYTE]) {
        status = MOTO_E2E_CRC_ERROR;
    } else {
        counter = (uint8_t)(data[MOTO_E2E_COUNTER_BYTE] & MOTO_E2E_COUNTER_MASK);
        if ((rx->armed != 0u) && ((uint32_t)(now_ms - rx->ref_ms) > rx->timeout_ms)) {
            /* Too long since the last OK frame (or since arming): the counter may have
             * wrapped, so the sequence cannot be trusted. Start over. */
            rx->armed = 0u;
            rx->has_ok = 0u;
        }
        if (rx->armed == 0u) {
            rx->armed = 1u;
            rx->has_ok = 0u;
            rx->last_counter = counter;
            rx->ref_ms = now_ms;
            status = MOTO_E2E_INITIAL;
        } else {
            delta = (uint8_t)((uint8_t)(counter - rx->last_counter) & MOTO_E2E_COUNTER_MASK);
            if (delta == 0u) {
                status = MOTO_E2E_REPEATED;
            } else if (delta > MOTO_E2E_MAX_DELTA_COUNTER) {
                rx->last_counter = counter;
                status = MOTO_E2E_WRONG_SEQUENCE;
            } else {
                rx->last_counter = counter;
                rx->ref_ms = now_ms;
                rx->has_ok = 1u;
                status = MOTO_E2E_OK;
            }
        }
    }
    return status;
}

moto_e2e_status_t moto_e2e_check_timeout(const moto_e2e_rx_state_t *rx, uint32_t now_ms)
{
    moto_e2e_status_t status = MOTO_E2E_OK;
    if ((rx == NULL) || (rx->has_ok == 0u) ||
        ((uint32_t)(now_ms - rx->ref_ms) > rx->timeout_ms)) {
        status = MOTO_E2E_TIMEOUT;
    }
    return status;
}
"""

E2E_PY = '''# E2E protect/check for host tools (same algorithm as gen/c/<node>/moto_e2e.c).

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

COUNTER_MASK = 0x0F
MAX_DELTA_COUNTER = 1
MIN_LENGTH = 2
MAX_LENGTH = 8
_U32 = 0xFFFFFFFF


class E2EStatus(Enum):
    OK = 0
    INITIAL = 1
    BAD_LENGTH = 2
    CRC_ERROR = 3
    REPEATED = 4
    WRONG_SEQUENCE = 5
    TIMEOUT = 6


def crc8(data_id: int, data: bytes | bytearray) -> int:
    """CRC8 SAE J1850 over DataID (low, high) and data[1:]."""
    crc = 0xFF
    for byte in bytes((data_id & 0xFF, (data_id >> 8) & 0xFF)) + bytes(data[1:]):
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1D) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc ^ 0xFF


@dataclass
class TxState:
    counter: int = 0


@dataclass
class RxState:
    timeout_ms: int
    ref_ms: int = 0
    last_counter: int = 0
    armed: bool = False
    has_ok: bool = False


def protect(data_id: int, data: bytearray, tx: TxState) -> None:
    if not MIN_LENGTH <= len(data) <= MAX_LENGTH:
        raise ValueError("E2E frame length must be 2..8 bytes")
    data[1] = (data[1] & 0xF0) | (tx.counter & COUNTER_MASK)
    data[0] = crc8(data_id, data)
    tx.counter = (tx.counter + 1) & COUNTER_MASK


def check(data_id: int, data: bytes | bytearray, rx: RxState, now_ms: int) -> E2EStatus:
    if not MIN_LENGTH <= len(data) <= MAX_LENGTH:
        return E2EStatus.BAD_LENGTH
    if crc8(data_id, data) != data[0]:
        return E2EStatus.CRC_ERROR
    counter = data[1] & COUNTER_MASK
    if rx.armed and ((now_ms - rx.ref_ms) & _U32) > rx.timeout_ms:
        rx.armed = False
        rx.has_ok = False
    if not rx.armed:
        rx.armed, rx.has_ok, rx.last_counter, rx.ref_ms = True, False, counter, now_ms
        return E2EStatus.INITIAL
    delta = (counter - rx.last_counter) & COUNTER_MASK
    if delta == 0:
        return E2EStatus.REPEATED
    rx.last_counter = counter
    if delta > MAX_DELTA_COUNTER:
        return E2EStatus.WRONG_SEQUENCE
    rx.ref_ms = now_ms
    rx.has_ok = True
    return E2EStatus.OK


def check_timeout(rx: RxState, now_ms: int) -> E2EStatus:
    if not rx.has_ok or ((now_ms - rx.ref_ms) & _U32) > rx.timeout_ms:
        return E2EStatus.TIMEOUT
    return E2EStatus.OK
'''

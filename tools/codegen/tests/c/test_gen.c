/* Host test of the generated C for one node (compiled by test_gen_c.py). */
#include <stdio.h>
#include <string.h>

#include "moto_e2e.h"
#include "platform.h"
#include "platform_meta.h"
#ifdef HAVE_VEHICLE
#include "vehicle_cl250.h"
#endif

static int failures = 0;
#define EXPECT(cond)                                                     \
    do {                                                                 \
        if (!(cond)) {                                                   \
            printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond);      \
            failures++;                                                  \
        }                                                                \
    } while (0)

static void test_crc_check_value(void)
{
    /* CRC-8/SAE-J1850("123456789") = 0x4B; DataID supplies "1","2". */
    const uint8_t data[8] = {0u, '3', '4', '5', '6', '7', '8', '9'};
    EXPECT(moto_e2e_crc8(0x3231u, data, 8u) == 0x4Bu);
}

static void make_frames(uint16_t data_id, uint8_t f[][4], uint8_t n)
{
    moto_e2e_tx_state_t tx;
    uint8_t i;
    moto_e2e_tx_init(&tx);
    for (i = 0u; i < n; i++) {
        memset(f[i], 0, 4u);
        f[i][2] = i;
        EXPECT(moto_e2e_protect(data_id, f[i], 4u, &tx) == MOTO_E2E_OK);
    }
}

static void test_protect_check(void)
{
    moto_e2e_rx_state_t rx;
    uint8_t f[20][4];
    uint8_t nine[9] = {0u};
    uint32_t t;
    uint8_t i;
    make_frames(48u, f, 20u);
    moto_e2e_rx_init(&rx, 300u);
    EXPECT(moto_e2e_check_timeout(&rx, 0u) == MOTO_E2E_TIMEOUT);
    EXPECT(moto_e2e_check(48u, f[0], 4u, &rx, 0u) == MOTO_E2E_INITIAL);
    EXPECT(moto_e2e_check_timeout(&rx, 0u) == MOTO_E2E_TIMEOUT);
    EXPECT(moto_e2e_check(48u, f[1], 4u, &rx, 100u) == MOTO_E2E_OK);
    EXPECT(moto_e2e_check(48u, f[1], 4u, &rx, 200u) == MOTO_E2E_REPEATED);
    EXPECT(moto_e2e_check(48u, f[3], 4u, &rx, 300u) == MOTO_E2E_WRONG_SEQUENCE);
    EXPECT(moto_e2e_check(48u, f[4], 4u, &rx, 350u) == MOTO_E2E_OK);
    EXPECT(moto_e2e_check_timeout(&rx, 650u) == MOTO_E2E_OK);
    EXPECT(moto_e2e_check_timeout(&rx, 651u) == MOTO_E2E_TIMEOUT);
    f[5][2] ^= 1u;
    EXPECT(moto_e2e_check(48u, f[5], 4u, &rx, 400u) == MOTO_E2E_CRC_ERROR);
    EXPECT(moto_e2e_check(33u, f[6], 4u, &rx, 400u) == MOTO_E2E_CRC_ERROR); /* wrong DataID */
    EXPECT(moto_e2e_check(48u, f[0], 1u, &rx, 400u) == MOTO_E2E_BAD_LENGTH);
    EXPECT(moto_e2e_check(48u, nine, 9u, &rx, 400u) == MOTO_E2E_BAD_LENGTH);
    EXPECT(moto_e2e_protect(48u, nine, 9u, NULL) == MOTO_E2E_BAD_LENGTH);

    /* Counter wrap 15 -> 0 stays OK. */
    make_frames(48u, f, 20u); /* f[5] was corrupted above */
    moto_e2e_rx_init(&rx, 300u);
    t = 0u;
    for (i = 0u; i < 20u; i++) {
        EXPECT(moto_e2e_check(48u, f[i], 4u, &rx, t) == ((i == 0u) ? MOTO_E2E_INITIAL : MOTO_E2E_OK));
        t += 100u;
    }

    /* 16 lost frames: counter looks like +1, but the gap exceeds the timeout. */
    moto_e2e_rx_init(&rx, 60u);
    EXPECT(moto_e2e_check(48u, f[0], 4u, &rx, 0u) == MOTO_E2E_INITIAL);
    EXPECT(moto_e2e_check(48u, f[1], 4u, &rx, 20u) == MOTO_E2E_OK);
    EXPECT(moto_e2e_check(48u, f[18], 4u, &rx, 340u) == MOTO_E2E_INITIAL);
    EXPECT(moto_e2e_check(48u, f[19], 4u, &rx, 360u) == MOTO_E2E_OK);

    /* Frozen sender (same frame repeated) resumes after the timeout: INITIAL first. */
    moto_e2e_rx_init(&rx, 300u);
    EXPECT(moto_e2e_check(48u, f[0], 4u, &rx, 0u) == MOTO_E2E_INITIAL);
    EXPECT(moto_e2e_check(48u, f[1], 4u, &rx, 100u) == MOTO_E2E_OK);
    EXPECT(moto_e2e_check(48u, f[1], 4u, &rx, 200u) == MOTO_E2E_REPEATED);
    EXPECT(moto_e2e_check_timeout(&rx, 5000u) == MOTO_E2E_TIMEOUT);
    EXPECT(moto_e2e_check(48u, f[2], 4u, &rx, 5000u) == MOTO_E2E_INITIAL);

    /* now_ms wrap-around inside check and check_timeout. */
    moto_e2e_rx_init(&rx, 300u);
    EXPECT(moto_e2e_check(48u, f[0], 4u, &rx, 0xFFFFFF00u) == MOTO_E2E_INITIAL);
    EXPECT(moto_e2e_check(48u, f[1], 4u, &rx, 0x10u) == MOTO_E2E_OK);
    EXPECT(moto_e2e_check_timeout(&rx, 0x20u) == MOTO_E2E_OK);
}

#ifdef HAVE_VEHICLE
/* Wraps a UDS request into a primary-ID single frame and asks the frame guard. */
static bool request_ok(const uint8_t *req, uint8_t len)
{
    uint8_t frame[8] = {0u, 0xAAu, 0xAAu, 0xAAu, 0xAAu, 0xAAu, 0xAAu, 0xAAu};
    uint8_t i;
    frame[0] = len;
    for (i = 0u; (i < len) && (i < 7u); i++) {
        frame[i + 1u] = req[i];
    }
    return vehicle_cl250_frame_allowed(VEHICLE_CL250_REQUEST_ID, true, frame, 8u);
}

static void test_vehicle(void)
{
    const uint8_t rpm[2] = {0x1Fu, 0x40u}; /* 8000 / 4 = 2000 rpm */
    const uint8_t volt[2] = {0x30u, 0x70u}; /* 12400 mV */
    const uint8_t ect[1] = {130u};
    float v = -1.0f;
    const uint8_t ok1[2] = {0x10u, 0x03u};
    const uint8_t ok2[2] = {0x3Eu, 0x80u};
    const uint8_t ok3[3] = {0x22u, 0xF4u, 0x0Cu};
    const uint8_t bad1[2] = {0x10u, 0x02u};
    const uint8_t bad2[2] = {0x11u, 0x01u};
    const uint8_t bad3[4] = {0x14u, 0xFFu, 0xFFu, 0xFFu};
    const uint8_t bad4[3] = {0x2Eu, 0xF1u, 0x90u};
    const uint8_t bad5[1] = {0x10u};
    const uint8_t bad6[2] = {0x10u, 0x83u};
    const uint8_t bad7[2] = {0x22u, 0xF4u};
    const uint8_t bad8[1] = {0x01u};
    const uint8_t fr_ok[8] = {0x03u, 0x22u, 0xF4u, 0x0Cu, 0xAAu, 0xAAu, 0xAAu, 0xAAu};
    const uint8_t fr_tp[8] = {0x02u, 0x3Eu, 0x80u, 0xAAu, 0xAAu, 0xAAu, 0xAAu, 0xAAu};
    const uint8_t fr_obd04[8] = {0x01u, 0x04u, 0xAAu, 0xAAu, 0xAAu, 0xAAu, 0xAAu, 0xAAu};
    const uint8_t fr_ff[8] = {0x10u, 0x14u, 0x22u, 0xF4u, 0x0Cu, 0xAAu, 0xAAu, 0xAAu};
    const uint8_t fr_prog[8] = {0x02u, 0x10u, 0x02u, 0xAAu, 0xAAu, 0xAAu, 0xAAu, 0xAAu};
    const uint8_t fr_long[4] = {0x05u, 0x22u, 0xF4u, 0x0Cu};

    EXPECT(vehicle_cl250_frame_allowed(VEHICLE_CL250_REQUEST_ID, true, fr_ok, 8u));
    EXPECT(vehicle_cl250_frame_allowed(VEHICLE_CL250_FALLBACK_REQUEST_ID, false, fr_tp, 8u));
    EXPECT(!vehicle_cl250_frame_allowed(VEHICLE_CL250_REQUEST_ID, false, fr_ok, 8u));
    EXPECT(!vehicle_cl250_frame_allowed(0x7DFu, false, fr_ok, 8u));
    EXPECT(!vehicle_cl250_frame_allowed(VEHICLE_CL250_RESPONSE_ID, true, fr_ok, 8u));
    EXPECT(!vehicle_cl250_frame_allowed(VEHICLE_CL250_REQUEST_ID, true, fr_obd04, 8u));
    EXPECT(!vehicle_cl250_frame_allowed(VEHICLE_CL250_REQUEST_ID, true, fr_ff, 8u));
    EXPECT(!vehicle_cl250_frame_allowed(VEHICLE_CL250_REQUEST_ID, true, fr_prog, 8u));
    EXPECT(!vehicle_cl250_frame_allowed(VEHICLE_CL250_REQUEST_ID, true, fr_long, 4u));
    EXPECT(!vehicle_cl250_frame_allowed(VEHICLE_CL250_REQUEST_ID, true, NULL, 8u));
    EXPECT(!request_ok(bad6, 2u));
    EXPECT(!request_ok(bad7, 2u));
    EXPECT(!request_ok(bad8, 1u));

    EXPECT(vehicle_cl250_decode(vehicle_cl250_find_did(VEHICLE_CL250_DID_ENGINE_SPEED), rpm, 2u, &v));
    EXPECT(v == 2000.0f);
    EXPECT(!vehicle_cl250_decode(vehicle_cl250_find_did(VEHICLE_CL250_DID_ENGINE_SPEED), rpm, 1u, &v));
    EXPECT(vehicle_cl250_decode(vehicle_cl250_find_did(VEHICLE_CL250_DID_BATTERY_VOLTAGE), volt, 2u, &v));
    EXPECT(v > 12.399f && v < 12.401f);
    EXPECT(vehicle_cl250_decode(vehicle_cl250_find_did(VEHICLE_CL250_DID_COOLANT_TEMPERATURE), ect, 1u, &v));
    EXPECT(v == 90.0f);
    EXPECT(vehicle_cl250_find_did(0x1234u) == NULL);
    EXPECT(request_ok(ok1, 2u));
    EXPECT(request_ok(ok2, 2u));
    EXPECT(request_ok(ok3, 3u));
    EXPECT(!request_ok(bad1, 2u));
    EXPECT(!request_ok(bad2, 2u));
    EXPECT(!request_ok(bad3, 4u));
    EXPECT(!request_ok(bad4, 3u));
    EXPECT(!request_ok(bad5, 1u));
}
#endif

int main(void)
{
    test_crc_check_value();
    test_protect_check();
#ifdef HAVE_VEHICLE
    test_vehicle();
#endif
    printf("%s\n", failures == 0 ? "ALL PASS" : "FAILURES");
    return failures == 0 ? 0 : 1;
}

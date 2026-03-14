/**
 * @file  test_lookup_table.c
 * @brief Unit tests for generated lookup table interpolation.
 */

#include <stdio.h>
#include <math.h>
#include "temp_sensor_controller.h"

static int tests_passed = 0;
static int tests_failed = 0;

#define ASSERT_NEAR(actual, expected, tol, msg) \
    do { \
        double _a = (double)(actual); \
        double _e = (double)(expected); \
        if (fabs(_a - _e) < (tol)) { \
            tests_passed++; \
        } else { \
            printf("FAIL: %s: expected %.6f, got %.6f\n", msg, _e, _a); \
            tests_failed++; \
        } \
    } while (0)

static void test_init_zeroes_output(void)
{
    temp_sensor_initialize();
    ASSERT_NEAR(temp_sensor_Y.temperature, 0.0, 1e-10, "Init zeroes temperature");
    ASSERT_NEAR(temp_sensor_U.voltage, 0.0, 1e-10, "Init zeroes voltage");
}

static void test_exact_breakpoint(void)
{
    temp_sensor_initialize();
    temp_sensor_U.voltage = 1.0;
    temp_sensor_step();
    ASSERT_NEAR(temp_sensor_Y.temperature, 90.0, 1e-6,
                "Exact breakpoint at 1.0V -> 90 degC");
}

static void test_interpolation_midpoint(void)
{
    temp_sensor_initialize();
    temp_sensor_U.voltage = 0.75;
    temp_sensor_step();
    /* Midpoint of [0.5, 1.0] -> midpoint of [120.0, 90.0] = 105.0 */
    ASSERT_NEAR(temp_sensor_Y.temperature, 105.0, 1e-6,
                "Midpoint interpolation 0.75V -> 105 degC");
}

static void test_clamp_below_range(void)
{
    temp_sensor_initialize();
    temp_sensor_U.voltage = 0.0;
    temp_sensor_step();
    ASSERT_NEAR(temp_sensor_Y.temperature, 120.0, 1e-6,
                "Below range clamps to first value 120 degC");
}

static void test_clamp_above_range(void)
{
    temp_sensor_initialize();
    temp_sensor_U.voltage = 5.0;
    temp_sensor_step();
    ASSERT_NEAR(temp_sensor_Y.temperature, -10.0, 1e-6,
                "Above range clamps to last value -10 degC");
}

static void test_interpolation_arbitrary(void)
{
    temp_sensor_initialize();
    temp_sensor_U.voltage = 2.25;
    temp_sensor_step();
    /* 2.25 is midpoint of [2.0, 2.5] -> midpoint of [45.0, 28.0] = 36.5 */
    ASSERT_NEAR(temp_sensor_Y.temperature, 36.5, 1e-6,
                "Arbitrary interpolation 2.25V -> 36.5 degC");
}

int main(void)
{
    printf("Running lookup table tests...\n\n");

    test_init_zeroes_output();
    test_exact_breakpoint();
    test_interpolation_midpoint();
    test_clamp_below_range();
    test_clamp_above_range();
    test_interpolation_arbitrary();

    printf("\n%d passed, %d failed\n", tests_passed, tests_failed);
    return tests_failed > 0 ? 1 : 0;
}

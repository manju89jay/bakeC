/**
 * @file  test_pid_controller.c
 * @brief Unit tests for generated PID controller implementation.
 */

#include <stdio.h>
#include <math.h>
#include "pid_pressure_controller.h"

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
    pid_pressure_initialize();
    ASSERT_NEAR(pid_pressure_Y.command, 0.0, 1e-10, "Init zeroes command output");
    ASSERT_NEAR(pid_pressure_U.setpoint, 0.0, 1e-10, "Init zeroes setpoint input");
    ASSERT_NEAR(pid_pressure_U.measured, 0.0, 1e-10, "Init zeroes measured input");
}

static void test_proportional_response(void)
{
    pid_pressure_initialize();
    pid_pressure_U.setpoint = 10.0;
    pid_pressure_U.measured = 0.0;
    pid_pressure_step();

    /* First step: error=10, Kp=2.5 -> p_term=25.0
     * integral = 10*0.001 = 0.01, Ki=0.8 -> i_term=0.008
     * d_term = 0.1 * (10-0)/0.001 = 1000 (capped by saturation)
     * output = 25 + 0.008 + 1000 = 1025.008 -> clamped to 1000 */
    ASSERT_NEAR(pid_pressure_Y.command, 1000.0, 1e-6,
                "Large error saturates to output_max");
}

static void test_small_error_proportional(void)
{
    pid_pressure_initialize();
    pid_pressure_U.setpoint = 1.0;
    pid_pressure_U.measured = 0.9;

    /* Step once to set prev_error, then step again for clean derivative */
    pid_pressure_step();
    pid_pressure_initialize();
    pid_pressure_U.setpoint = 1.0;
    pid_pressure_U.measured = 0.9;
    pid_pressure_step();

    /* error=0.1, Kp=2.5 -> p_term=0.25
     * Total output is dominated by proportional for small first step */
    if (pid_pressure_Y.command > 0.0) {
        tests_passed++;
    } else {
        printf("FAIL: Small positive error should produce positive output, got %.6f\n",
               pid_pressure_Y.command);
        tests_failed++;
    }
}

static void test_output_saturation(void)
{
    pid_pressure_initialize();

    /* Large positive error -> output should be clamped to 1000.0 */
    pid_pressure_U.setpoint = 500.0;
    pid_pressure_U.measured = 0.0;
    pid_pressure_step();
    ASSERT_NEAR(pid_pressure_Y.command, 1000.0, 1e-6,
                "Large positive error clamps to +1000");

    pid_pressure_initialize();

    /* Large negative error -> output should be clamped to -1000.0 */
    pid_pressure_U.setpoint = 0.0;
    pid_pressure_U.measured = 500.0;
    pid_pressure_step();
    ASSERT_NEAR(pid_pressure_Y.command, -1000.0, 1e-6,
                "Large negative error clamps to -1000");
}

static void test_anti_windup(void)
{
    pid_pressure_initialize();

    /* Accumulate large integral by stepping many times with constant error */
    pid_pressure_U.setpoint = 100.0;
    pid_pressure_U.measured = 0.0;
    for (int i = 0; i < 50000; i++) {
        pid_pressure_step();
    }

    /* Now remove the error — output should recover, not stay stuck at max */
    pid_pressure_U.setpoint = 0.0;
    pid_pressure_U.measured = 0.0;
    for (int i = 0; i < 100; i++) {
        pid_pressure_step();
    }

    /* With anti-windup, integral is bounded to [-1000, 1000], so output
     * should be near Ki * integral_max = 0.8 * 1000 = 800 at most,
     * and should decrease toward 0 with zero error */
    if (pid_pressure_Y.command < 1000.0) {
        tests_passed++;
    } else {
        printf("FAIL: Anti-windup should prevent output from staying at max, got %.6f\n",
               pid_pressure_Y.command);
        tests_failed++;
    }
}

int main(void)
{
    printf("Running PID controller tests...\n\n");

    test_init_zeroes_output();
    test_proportional_response();
    test_small_error_proportional();
    test_output_saturation();
    test_anti_windup();

    printf("\n%d passed, %d failed\n", tests_passed, tests_failed);
    return tests_failed > 0 ? 1 : 0;
}

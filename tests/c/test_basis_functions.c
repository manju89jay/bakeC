/**
 * @file  test_basis_functions.c
 * @brief Unit tests for generated basis function implementations.
 */

#include <stdio.h>
#include <math.h>
#include "mnarx_lung_controller.h"

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
    mnarx_lung_initialize();
    ASSERT_NEAR(mnarx_lung_Y.Paw, 0.0, 1e-10, "Init zeroes Paw output");
}

static void test_zero_input_zero_output(void)
{
    mnarx_lung_initialize();
    mnarx_lung_U.flow = 0.0;
    mnarx_lung_U.volume = 0.0;
    mnarx_lung_step();
    ASSERT_NEAR(mnarx_lung_Y.Paw, 0.0, 1e-6, "Zero input produces zero output");
}

static void test_nonzero_volume_produces_output(void)
{
    mnarx_lung_initialize();
    mnarx_lung_U.flow = 0.5;
    mnarx_lung_U.volume = 0.4;

    for (int i = 0; i < 10; i++) {
        mnarx_lung_step();
    }

    if (mnarx_lung_Y.Paw > 0.0) {
        tests_passed++;
    } else {
        printf("FAIL: Expected positive Paw with positive inputs, got %.6f\n",
               mnarx_lung_Y.Paw);
        tests_failed++;
    }
}

int main(void)
{
    printf("Running basis function tests...\n\n");

    test_init_zeroes_output();
    test_zero_input_zero_output();
    test_nonzero_volume_produces_output();

    printf("\n%d passed, %d failed\n", tests_passed, tests_failed);
    return tests_failed > 0 ? 1 : 0;
}

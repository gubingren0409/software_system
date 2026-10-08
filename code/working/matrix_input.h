#ifndef MATRIX_INPUT_H
#define MATRIX_INPUT_H

#include <stdint.h>
#include <string.h>

#define INPUT_GENERATOR_VERSION "splitmix64-interleaved-v1"

enum input_pattern {
    INPUT_RANDOM = 0,
    INPUT_ZERO = 1,
    INPUT_IDENTITY = 2
};

static uint64_t splitmix64_next(uint64_t *state) {
    uint64_t value = (*state += UINT64_C(0x9e3779b97f4a7c15));
    value = (value ^ (value >> 30)) * UINT64_C(0xbf58476d1ce4e5b9);
    value = (value ^ (value >> 27)) * UINT64_C(0x94d049bb133111eb);
    return value ^ (value >> 31);
}

static double random_unit(uint64_t *state) {
    return (double)(splitmix64_next(state) >> 11) * 0x1.0p-53;
}

static const char *input_pattern_name(enum input_pattern pattern) {
    switch (pattern) {
        case INPUT_RANDOM:
            return "random";
        case INPUT_ZERO:
            return "zero";
        case INPUT_IDENTITY:
            return "identity";
    }
    return "unknown";
}

static int parse_input_pattern(const char *text, enum input_pattern *pattern) {
    if (strcmp(text, "random") == 0) {
        *pattern = INPUT_RANDOM;
        return 1;
    }
    if (strcmp(text, "zero") == 0) {
        *pattern = INPUT_ZERO;
        return 1;
    }
    if (strcmp(text, "identity") == 0) {
        *pattern = INPUT_IDENTITY;
        return 1;
    }
    return 0;
}

static void initialize_inputs(double *a, double *b, int n, uint64_t seed,
                              enum input_pattern pattern) {
    uint64_t state = seed;
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            const size_t index = (size_t)i * (size_t)n + (size_t)j;
            if (pattern == INPUT_RANDOM) {
                /* Preserve the teacher program's interleaved A/B fill order. */
                a[index] = random_unit(&state);
                b[index] = random_unit(&state);
            } else if (pattern == INPUT_IDENTITY) {
                a[index] = i == j ? 1.0 : 0.0;
                b[index] = i == j ? 1.0 : 0.0;
            } else {
                a[index] = 0.0;
                b[index] = 0.0;
            }
        }
    }
}

#endif

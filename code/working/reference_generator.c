#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <inttypes.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "matrix_input.h"

#ifndef MATRIX_N
#define MATRIX_N 4096
#endif

#ifndef ABS_TOL
#define ABS_TOL 1e-12L
#endif

#ifndef REL_TOL
#define REL_TOL 1e-12L
#endif

static double A[MATRIX_N][MATRIX_N];
static double B[MATRIX_N][MATRIX_N];

struct options {
    uint64_t seed;
    enum input_pattern input;
    const char *output_path;
    int use_long_double;
};

static int parse_seed(const char *text, uint64_t *value) {
    if (text[0] == '\0') {
        return 0;
    }
    for (const unsigned char *cursor = (const unsigned char *)text;
         *cursor != '\0'; ++cursor) {
        if (*cursor < (unsigned char)'0' || *cursor > (unsigned char)'9') {
            return 0;
        }
    }
    char *end = NULL;
    errno = 0;
    const uintmax_t parsed = strtoumax(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0' || parsed > UINT64_MAX) {
        return 0;
    }
    *value = (uint64_t)parsed;
    return 1;
}

static int parse_options(int argc, char **argv, struct options *options) {
    int seen_seed = 0;
    int seen_input = 0;
    int seen_output = 0;
    int seen_accumulator = 0;
    if (argc != 9) {
        return 0;
    }
    for (int i = 1; i < argc; i += 2) {
        if (strcmp(argv[i], "--seed") == 0 && !seen_seed) {
            if (!parse_seed(argv[i + 1], &options->seed)) {
                return 0;
            }
            seen_seed = 1;
        } else if (strcmp(argv[i], "--input") == 0 && !seen_input) {
            if (!parse_input_pattern(argv[i + 1], &options->input)) {
                return 0;
            }
            seen_input = 1;
        } else if (strcmp(argv[i], "--output") == 0 && !seen_output) {
            options->output_path = argv[i + 1];
            seen_output = options->output_path[0] != '\0';
        } else if (strcmp(argv[i], "--accumulator") == 0 &&
                   !seen_accumulator) {
            if (strcmp(argv[i + 1], "long-double") == 0) {
                options->use_long_double = 1;
            } else if (strcmp(argv[i + 1], "double") == 0) {
                options->use_long_double = 0;
            } else {
                return 0;
            }
            seen_accumulator = 1;
        } else {
            return 0;
        }
    }
    return seen_seed && seen_input && seen_output && seen_accumulator;
}

static double seconds_between(const struct timespec *start,
                              const struct timespec *end) {
    return (double)(end->tv_sec - start->tv_sec) +
           1e-9 * (double)(end->tv_nsec - start->tv_nsec);
}

static size_t sample_coordinates(int coordinates[][2], size_t capacity) {
    const int candidates[][2] = {
        {0, 0},
        {0, MATRIX_N - 1},
        {MATRIX_N - 1, 0},
        {MATRIX_N - 1, MATRIX_N - 1},
        {MATRIX_N / 2, MATRIX_N / 2},
        {MATRIX_N / 4, MATRIX_N / 4},
        {MATRIX_N / 4, 3 * MATRIX_N / 4},
        {3 * MATRIX_N / 4, MATRIX_N / 4},
        {3 * MATRIX_N / 4, 3 * MATRIX_N / 4},
        {1, MATRIX_N / 3},
        {MATRIX_N / 3, 1},
        {MATRIX_N / 3, 2 * MATRIX_N / 3},
        {2 * MATRIX_N / 3, MATRIX_N / 3},
        {MATRIX_N - 2, MATRIX_N / 2},
        {MATRIX_N / 2, MATRIX_N - 2},
        {MATRIX_N / 7, 5 * MATRIX_N / 7},
    };
    size_t count = 0;
    const size_t candidate_count = sizeof(candidates) / sizeof(candidates[0]);
    for (size_t k = 0; k < candidate_count && count < capacity; ++k) {
        const int i = candidates[k][0];
        const int j = candidates[k][1];
        if (i < 0 || i >= MATRIX_N || j < 0 || j >= MATRIX_N) {
            continue;
        }
        int duplicate = 0;
        for (size_t prior = 0; prior < count; ++prior) {
            if (coordinates[prior][0] == i && coordinates[prior][1] == j) {
                duplicate = 1;
                break;
            }
        }
        if (!duplicate) {
            coordinates[count][0] = i;
            coordinates[count][1] = j;
            ++count;
        }
    }
    return count;
}

int main(int argc, char **argv) {
    struct options options = {0};
    if (!parse_options(argc, argv, &options)) {
        fprintf(stderr, "invalid reference-generator arguments\n");
        return 64;
    }

    initialize_inputs(&A[0][0], &B[0][0], MATRIX_N, options.seed,
                      options.input);
    const size_t count = (size_t)MATRIX_N * (size_t)MATRIX_N;
    double *output = calloc(count, sizeof(*output));
    if (output == NULL) {
        fprintf(stderr, "reference allocation failed\n");
        return 70;
    }

    struct timespec start;
    struct timespec end;
    if (clock_gettime(CLOCK_MONOTONIC, &start) != 0) {
        perror("clock_gettime(start)");
        free(output);
        return 70;
    }

    if (options.use_long_double) {
        for (int i = 0; i < MATRIX_N; ++i) {
            for (int j = 0; j < MATRIX_N; ++j) {
                long double sum = 0.0L;
                for (int k = 0; k < MATRIX_N; ++k) {
                    sum += (long double)A[i][k] * (long double)B[k][j];
                }
                output[(size_t)i * (size_t)MATRIX_N + (size_t)j] =
                    (double)sum;
            }
        }
    } else {
        /* Independent non-blocked i-k-j reference implementation. */
        for (int i = 0; i < MATRIX_N; ++i) {
            for (int k = 0; k < MATRIX_N; ++k) {
                const double aik = A[i][k];
                for (int j = 0; j < MATRIX_N; ++j) {
                    output[(size_t)i * (size_t)MATRIX_N + (size_t)j] +=
                        aik * B[k][j];
                }
            }
        }
    }

    if (clock_gettime(CLOCK_MONOTONIC, &end) != 0) {
        perror("clock_gettime(end)");
        free(output);
        return 70;
    }
    const double generation_seconds = seconds_between(&start, &end);

    uint64_t nonfinite_count = 0;
    uint64_t analytic_mismatch_count = 0;
    long double checksum = 0.0L;
    for (int i = 0; i < MATRIX_N; ++i) {
        for (int j = 0; j < MATRIX_N; ++j) {
            const double value = output[(size_t)i * (size_t)MATRIX_N +
                                        (size_t)j];
            if (!isfinite(value)) {
                ++nonfinite_count;
            }
            checksum += (long double)value;
            if (options.input != INPUT_RANDOM) {
                const double expected =
                    options.input == INPUT_IDENTITY && i == j ? 1.0 : 0.0;
                if (value != expected) {
                    ++analytic_mismatch_count;
                }
            }
        }
    }

    int coordinates[16][2];
    const size_t sample_count = sample_coordinates(coordinates, 16);
    uint64_t sample_mismatch_count = 0;
    long double sample_max_abs_error = 0.0L;
    long double sample_max_rel_error = 0.0L;
    for (size_t sample = 0; sample < sample_count; ++sample) {
        const int i = coordinates[sample][0];
        const int j = coordinates[sample][1];
        long double expected = 0.0L;
        for (int k = 0; k < MATRIX_N; ++k) {
            expected += (long double)A[i][k] * (long double)B[k][j];
        }
        const double actual =
            output[(size_t)i * (size_t)MATRIX_N + (size_t)j];
        const long double abs_error = fabsl((long double)actual - expected);
        const long double rel_error =
            expected == 0.0L ? (abs_error == 0.0L ? 0.0L : INFINITY)
                             : abs_error / fabsl(expected);
        const long double tolerance = ABS_TOL + REL_TOL * fabsl(expected);
        if (!isfinite(expected) || !isfinite(actual) || !isfinite(abs_error) ||
            !isfinite(rel_error) || abs_error > tolerance) {
            ++sample_mismatch_count;
        }
        if (isfinite(abs_error) && abs_error > sample_max_abs_error) {
            sample_max_abs_error = abs_error;
        }
        if (isfinite(rel_error) && rel_error > sample_max_rel_error) {
            sample_max_rel_error = rel_error;
        }
    }

    const int valid = generation_seconds > 0.0 && isfinite(generation_seconds) &&
                      isfinite(checksum) && nonfinite_count == 0 &&
                      analytic_mismatch_count == 0 && sample_mismatch_count == 0;
    if (!valid) {
        fprintf(stderr, "reference validation failed\n");
        free(output);
        return 65;
    }

    FILE *stream = fopen(options.output_path, "wb");
    if (stream == NULL) {
        perror("fopen(output)");
        free(output);
        return 70;
    }
    const size_t written = fwrite(output, sizeof(*output), count, stream);
    const int close_result = fclose(stream);
    free(output);
    if (written != count || close_result != 0) {
        fprintf(stderr, "reference write failed\n");
        return 70;
    }

    printf("{\"schema\":\"matrix-reference-v1\",\"status\":\"ok\","
           "\"n\":%d,\"seed\":%" PRIu64 ",\"input\":\"%s\","
           "\"input_generator\":\"%s\",\"accumulator\":\"%s\","
           "\"element_type\":\"float64-native-le\",\"element_count\":%zu,"
           "\"byte_count\":%zu,\"generation_seconds\":%.17g,"
           "\"checksum\":%.21Lg,\"nonfinite_count\":%" PRIu64 ","
           "\"analytic_mismatch_count\":%" PRIu64 ","
           "\"sample_rule\":\"fixed-coordinates-v1\","
           "\"sample_count\":%zu,\"sample_mismatch_count\":%" PRIu64 ","
           "\"sample_max_abs_error\":%.21Lg,"
           "\"sample_max_rel_error\":%.21Lg}\n",
           MATRIX_N, options.seed, input_pattern_name(options.input),
           INPUT_GENERATOR_VERSION,
           options.use_long_double ? "long-double" : "double", count,
           count * sizeof(*output), generation_seconds, checksum,
           nonfinite_count, analytic_mismatch_count, sample_count,
           sample_mismatch_count, sample_max_abs_error, sample_max_rel_error);
    return 0;
}

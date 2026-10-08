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

#ifndef MM_TEST_FAULT
#define MM_TEST_FAULT 0
#endif

static double A[MATRIX_N][MATRIX_N];
static double B[MATRIX_N][MATRIX_N];
static double C[MATRIX_N][MATRIX_N];

struct options {
    int block_size;
    uint64_t seed;
    enum input_pattern input;
    const char *reference_path;
};

static void print_number_or_null(long double value) {
    if (isfinite(value)) {
        printf("%.21Lg", value);
    } else {
        printf("null");
    }
}

static int reject_argument(const char *code) {
    printf("{\"schema\":\"matrix-multiplication-result-v1\","
           "\"status\":\"parameter_error\",\"error\":\"%s\"}\n",
           code);
    return 64;
}

static int parse_positive_int(const char *text, int *value) {
    char *end = NULL;
    errno = 0;
    const long parsed = strtol(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0' || parsed < 1 ||
        parsed > MATRIX_N) {
        return 0;
    }
    *value = (int)parsed;
    return 1;
}

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
    int seen_block = 0;
    int seen_seed = 0;
    int seen_input = 0;
    int seen_reference = 0;
    if (argc != 9) {
        return 0;
    }
    for (int i = 1; i < argc; i += 2) {
        if (i + 1 >= argc) {
            return 0;
        }
        if (strcmp(argv[i], "--block-size") == 0 && !seen_block) {
            if (!parse_positive_int(argv[i + 1], &options->block_size)) {
                return 0;
            }
            seen_block = 1;
        } else if (strcmp(argv[i], "--seed") == 0 && !seen_seed) {
            if (!parse_seed(argv[i + 1], &options->seed)) {
                return 0;
            }
            seen_seed = 1;
        } else if (strcmp(argv[i], "--input") == 0 && !seen_input) {
            if (!parse_input_pattern(argv[i + 1], &options->input)) {
                return 0;
            }
            seen_input = 1;
        } else if (strcmp(argv[i], "--reference") == 0 && !seen_reference) {
            if (argv[i + 1][0] == '\0') {
                return 0;
            }
            options->reference_path = argv[i + 1];
            seen_reference = 1;
        } else {
            return 0;
        }
    }
    return seen_block && seen_seed && seen_input && seen_reference;
}

static double seconds_between(const struct timespec *start,
                              const struct timespec *end) {
    return (double)(end->tv_sec - start->tv_sec) +
           1e-9 * (double)(end->tv_nsec - start->tv_nsec);
}

int main(int argc, char **argv) {
    struct options options = {0};
    if (!parse_options(argc, argv, &options)) {
        return reject_argument("INVALID_ARGUMENT");
    }

    initialize_inputs(&A[0][0], &B[0][0], MATRIX_N, options.seed,
                      options.input);
    memset(C, 0, sizeof(C));

    struct timespec start;
    struct timespec end;
    if (clock_gettime(CLOCK_MONOTONIC, &start) != 0) {
        perror("clock_gettime(start)");
        return 70;
    }

    const int s = options.block_size;
    /* Teacher-provided core loop order and computation semantics. */
    for (int ih = 0; ih < MATRIX_N; ih += s)
        for (int jh = 0; jh < MATRIX_N; jh += s)
            for (int kh = 0; kh < MATRIX_N; kh += s)
                for (int il = 0; il < s && ih + il < MATRIX_N; ++il)
                    for (int kl = 0; kl < s && kh + kl < MATRIX_N; ++kl)
                        for (int jl = 0; jl < s && jh + jl < MATRIX_N; ++jl)
                            C[ih + il][jh + jl] +=
                                A[ih + il][kh + kl] * B[kh + kl][jh + jl];

    if (clock_gettime(CLOCK_MONOTONIC, &end) != 0) {
        perror("clock_gettime(end)");
        return 70;
    }
    double elapsed_seconds = seconds_between(&start, &end);

#if MM_TEST_FAULT == 1
    C[0][0] += 1.0;
#elif MM_TEST_FAULT == 2
    C[0][0] = NAN;
#elif MM_TEST_FAULT == 3
    C[0][0] = INFINITY;
#endif

    FILE *reference = fopen(options.reference_path, "rb");
    if (reference == NULL) {
        perror("fopen(reference)");
        return 70;
    }

    double *reference_row = malloc((size_t)MATRIX_N * sizeof(*reference_row));
    if (reference_row == NULL) {
        fprintf(stderr, "reference row allocation failed\n");
        fclose(reference);
        return 70;
    }

    long double checksum = 0.0L;
    long double reference_checksum = 0.0L;
    long double max_abs_error = 0.0L;
    long double max_rel_error = 0.0L;
    uint64_t mismatch_count = 0;
    uint64_t nonfinite_result_count = 0;
    uint64_t nonfinite_reference_count = 0;
    uint64_t nonfinite_error_count = 0;

    for (int i = 0; i < MATRIX_N; ++i) {
        if (fread(reference_row, sizeof(*reference_row), MATRIX_N, reference) !=
            (size_t)MATRIX_N) {
            fprintf(stderr, "reference is truncated at row %d\n", i);
            free(reference_row);
            fclose(reference);
            return 70;
        }
        for (int j = 0; j < MATRIX_N; ++j) {
            const double result_value = C[i][j];
            double reference_value = reference_row[j];
#if MM_TEST_FAULT == 4
            if (i == 0 && j == 0) {
                reference_value = NAN;
            }
#endif
            const int result_finite = isfinite(result_value);
            const int reference_finite = isfinite(reference_value);
            if (!result_finite) {
                ++nonfinite_result_count;
            }
            if (!reference_finite) {
                ++nonfinite_reference_count;
            }
            checksum += (long double)result_value;
            reference_checksum += (long double)reference_value;
            if (!result_finite || !reference_finite) {
                ++nonfinite_error_count;
                continue;
            }

            const long double abs_error =
                fabsl((long double)result_value - (long double)reference_value);
            const long double tolerance =
                ABS_TOL + REL_TOL * fabsl((long double)reference_value);
            long double rel_error = 0.0L;
            if (reference_value != 0.0) {
                rel_error = abs_error / fabsl((long double)reference_value);
            } else if (abs_error != 0.0L) {
                rel_error = INFINITY;
            }
            if (!isfinite(abs_error) || !isfinite(rel_error) ||
                !isfinite(tolerance)) {
                ++nonfinite_error_count;
                continue;
            }
            if (abs_error > max_abs_error) {
                max_abs_error = abs_error;
            }
            if (rel_error > max_rel_error) {
                max_rel_error = rel_error;
            }
            if (abs_error > tolerance) {
                ++mismatch_count;
            }
        }
    }

    const int trailing_byte = fgetc(reference);
    free(reference_row);
    fclose(reference);
    if (trailing_byte != EOF) {
        fprintf(stderr, "reference has trailing data\n");
        return 70;
    }

#if MM_TEST_FAULT == 5
    elapsed_seconds = NAN;
#elif MM_TEST_FAULT == 6
    checksum = NAN;
#elif MM_TEST_FAULT == 7
    max_abs_error = NAN;
#endif

    const int elapsed_finite = isfinite(elapsed_seconds) && elapsed_seconds > 0.0;
    const int checksum_finite = isfinite(checksum);
    const int reference_checksum_finite = isfinite(reference_checksum);
    const int error_summary_finite =
        isfinite(max_abs_error) && isfinite(max_rel_error);
    const int valid = elapsed_finite && checksum_finite &&
                      reference_checksum_finite && error_summary_finite &&
                      mismatch_count == 0 && nonfinite_result_count == 0 &&
                      nonfinite_reference_count == 0 &&
                      nonfinite_error_count == 0;

    printf("{\"schema\":\"matrix-multiplication-result-v1\","
           "\"status\":\"%s\",\"n\":%d,\"block_size\":%d,"
           "\"seed\":%" PRIu64 ",\"input\":\"%s\","
           "\"input_generator\":\"%s\",\"elapsed_seconds\":",
           valid ? "ok" : "validation_failed", MATRIX_N, options.block_size,
           options.seed, input_pattern_name(options.input),
           INPUT_GENERATOR_VERSION);
    print_number_or_null((long double)elapsed_seconds);
    printf(",\"checksum\":");
    print_number_or_null(checksum);
    printf(",\"reference_checksum\":");
    print_number_or_null(reference_checksum);
    printf(",\"max_abs_error\":");
    print_number_or_null(max_abs_error);
    printf(",\"max_rel_error\":");
    print_number_or_null(max_rel_error);
    printf(",\"abs_tol\":%.1Le,\"rel_tol\":%.1Le,"
           "\"checked_entries\":%" PRIu64 ","
           "\"mismatch_count\":%" PRIu64 ","
           "\"nonfinite_result_count\":%" PRIu64 ","
           "\"nonfinite_reference_count\":%" PRIu64 ","
           "\"nonfinite_error_count\":%" PRIu64 ","
           "\"finite_elapsed\":%s,\"finite_checksum\":%s,"
           "\"finite_reference_checksum\":%s,"
           "\"finite_error_summary\":%s,\"validation\":%s,"
           "\"fault_injection\":%d}\n",
           ABS_TOL, REL_TOL, (uint64_t)MATRIX_N * (uint64_t)MATRIX_N,
           mismatch_count, nonfinite_result_count, nonfinite_reference_count,
           nonfinite_error_count, elapsed_finite ? "true" : "false",
           checksum_finite ? "true" : "false",
           reference_checksum_finite ? "true" : "false",
           error_summary_finite ? "true" : "false",
           valid ? "true" : "false", MM_TEST_FAULT);
    return valid ? 0 : 65;
}

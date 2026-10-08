#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/time.h>

#ifndef MATRIX_N
#define MATRIX_N 65
#endif

static double A[MATRIX_N][MATRIX_N];
static double B[MATRIX_N][MATRIX_N];
static double C[MATRIX_N][MATRIX_N];
static long double reference[MATRIX_N][MATRIX_N];

static double tdiff(const struct timeval *start, const struct timeval *end) {
    return (double)(end->tv_sec - start->tv_sec) +
           1e-6 * (double)(end->tv_usec - start->tv_usec);
}

static void initialize(void) {
    srand(1);
    for (int i = 0; i < MATRIX_N; ++i) {
        for (int j = 0; j < MATRIX_N; ++j) {
            A[i][j] = (double)rand() / (double)RAND_MAX;
            B[i][j] = (double)rand() / (double)RAND_MAX;
            C[i][j] = 0.0;
            reference[i][j] = 0.0L;
        }
    }
}

static void multiply_reference(void) {
    for (int i = 0; i < MATRIX_N; ++i) {
        for (int j = 0; j < MATRIX_N; ++j) {
            for (int k = 0; k < MATRIX_N; ++k) {
                reference[i][j] +=
                    (long double)A[i][k] * (long double)B[k][j];
            }
        }
    }
}

int main(int argc, const char *argv[]) {
    assert(argc == 2);
    const int s = atoi(argv[1]);
    if (s < 1 || s > MATRIX_N) {
        fprintf(stderr, "Invalid input values.\n");
        return -1;
    }

    initialize();

    struct timeval start;
    struct timeval end;
    gettimeofday(&start, NULL);

    /* This is the teacher-provided blocked loop nest, unchanged in structure. */
    for (int ih = 0; ih < MATRIX_N; ih += s)
        for (int jh = 0; jh < MATRIX_N; jh += s)
            for (int kh = 0; kh < MATRIX_N; kh += s)
                for (int il = 0; il < s && ih + il < MATRIX_N; ++il)
                    for (int kl = 0; kl < s && kh + kl < MATRIX_N; ++kl)
                        for (int jl = 0; jl < s && jh + jl < MATRIX_N; ++jl)
                            C[ih + il][jh + jl] +=
                                A[ih + il][kh + kl] * B[kh + kl][jh + jl];

    gettimeofday(&end, NULL);

    multiply_reference();
    double checksum = 0.0;
    long double max_abs_error = 0.0L;
    long double max_rel_error = 0.0L;
    int failed_entries = 0;
    for (int i = 0; i < MATRIX_N; ++i) {
        for (int j = 0; j < MATRIX_N; ++j) {
            checksum += C[i][j];
            const long double error = fabsl((long double)C[i][j] - reference[i][j]);
            const long double relative_error =
                error / (fabsl(reference[i][j]) + 1e-30L);
            if (error > max_abs_error) {
                max_abs_error = error;
            }
            if (relative_error > max_rel_error) {
                max_rel_error = relative_error;
            }
            if (error > 1e-12L + 1e-12L * fabsl(reference[i][j])) {
                ++failed_entries;
            }
        }
    }

    printf("matrix_n=%d\n", MATRIX_N);
    printf("block_size=%d\n", s);
    printf("elapsed_seconds=%.9f\n", tdiff(&start, &end));
    printf("checksum=%.17g\n", checksum);
    printf("max_abs_error=%.17Le\n", max_abs_error);
    printf("max_rel_error=%.17Le\n", max_rel_error);
    printf("failed_entries=%d\n", failed_entries);
    printf("verification=%s\n", failed_entries == 0 ? "PASS" : "FAIL");
    return failed_entries == 0 ? 0 : 2;
}

/**
 * Copyright (c) 2013-2014 MIT License by 6.172 Staff
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to
 * deal in the Software without restriction, including without limitation the
 * rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
 * sell copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
 * FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
 * IN THE SOFTWARE.
 **/

#include <stdio.h>
#include <unistd.h>
#include <stdlib.h>
#include <assert.h>
#include <errno.h>
#include <getopt.h>
#include <limits.h>
#include <string.h>

#include "./fasttime.h"
#include "./tests.h"

// Extern variables
extern test_case test_cases[];


static void run_test_suite(int start_idx, int printFlag, int N, int R, int benchmarkOnly,
                           struct testFunc_t* testFunc, int numFunc) {
  for (int i = 0; test_cases[i] != NULL; i++) {
    if (benchmarkOnly && i > 0) {
      break;
    }
    if (i < start_idx) {
      continue;
    }
    fprintf(stderr, "\nRunning test #%d...\n", i);
    (*test_cases[i])(printFlag, N, R, testFunc, numFunc);
  }
  fprintf(stderr, "Done testing.\n");
}


extern void sort_a(data_t*, int, int);
extern void sort_i(data_t*, int, int);
extern void sort_p(data_t*, int, int);
extern void sort_c(data_t*, int, int);
extern void sort_m(data_t*, int, int);
extern void sort_f(data_t*, int, int);

static unsigned long parse_number(const char* text, unsigned long maximum,
                                  const char* label) {
  char* end;
  errno = 0;
  unsigned long value = strtoul(text, &end, 10);
  if (text[0] < '0' || text[0] > '9' || *end != '\0' ||
      errno == ERANGE || value > maximum) {
    fprintf(stderr, "Invalid %s: %s\n", label, text);
    exit(EXIT_FAILURE);
  }
  return value;
}

int main(int argc, char** argv) {
  int optchar, printFlag = 0, benchmarkOnly = 0;
  unsigned int seed = 1;
  const char* variant = "a";
  struct testFunc_t available[] = {
    {sort_a, "sort_a", 0}, {sort_i, "sort_i", 0}, {sort_p, "sort_p", 0},
    {sort_c, "sort_c", 0}, {sort_m, "sort_m", 0}, {sort_f, "sort_f", 0},
  };
  struct testFunc_t selected[6];
  int count = 0;
  const struct option options[] = {
    {"variant", required_argument, NULL, 'v'}, {NULL, 0, NULL, 0}
  };
  while ((optchar = getopt_long(argc, argv, "s:pbv:", options, NULL)) != -1) {
    switch (optchar) {
    case 's': seed = (unsigned int) parse_number(optarg, UINT_MAX, "seed"); break;
    case 'b': benchmarkOnly = 1; break;
    case 'p': printFlag = 1; break;
    case 'v': variant = optarg; break;
    default: return EXIT_FAILURE;
    }
  }
  if (argc - optind != 2) {
    fprintf(stderr, "Usage: %s [-p] [-b] [-s seed] [--variant a|i|p|c|m|f|all] N R\n", argv[0]);
    return EXIT_FAILURE;
  }
  // Keep p+r representable in the unchanged baseline midpoint calculation.
  int N = (int) parse_number(argv[optind], INT_MAX / 2, "N");
  int R = (int) parse_number(argv[optind + 1], INT_MAX, "R");
  if (N < 1 || R < 1) {
    fprintf(stderr, "N and R must be positive\n");
    return EXIT_FAILURE;
  }
  for (int i = 0; i < 6; i++) {
    if (strcmp(variant, "all") == 0 ||
        (strlen(variant) == 1 && variant[0] == available[i].name[5])) {
      selected[count++] = available[i];
    }
  }
  if (count == 0) {
    fprintf(stderr, "Unknown variant: %s\n", variant);
    return EXIT_FAILURE;
  }
  set_random_seed(seed);
  printf("Initial rand_r seed: %u; sort versions: %d; trials per input: %d\n", seed, count, R);
  for (int i = 0; i < count; i++) {
    printf("RUN variant=%s N=%d R=%d seed=%u group=%s timed_calls=%llu\n",
           selected[i].name, N, R, seed, benchmarkOnly ? "timing" : "full",
           2ULL * (unsigned int) R);
  }
  run_test_suite(0, printFlag, N, R, benchmarkOnly, selected, count);
  for (int i = 0; i < count; i++) {
    printf("TOTAL variant=%s N=%d R=%d seed=%u actual_sort_calls=%llu\n",
           selected[i].name, N, R, seed, selected[i].calls);
  }
  return 0;
}

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

int main(int argc, char** argv) {
  int N, R, optchar, printFlag = 0, benchmarkOnly = 0;
  unsigned int seed = 1;

  // an array of struct testFunc_t indicating the sort functions to test
  // the struct contains two fields --- the function pointer to the sort function
  // and its name (for printing)
  struct testFunc_t testFunc[] = {
    {&sort_a, "sort_a"},
    //{&sort_i, "sort_i\t\t"},
    //{&sort_p, "sort_p\t\t"},
    //{&sort_c, "sort_c\t\t"},
    //{&sort_m, "sort_m\t\t"},
    //{&sort_f, "sort_f\t\t"},
  };
  const int kNumOfFunc = sizeof(testFunc) / sizeof(testFunc[0]);

  // process command line options
  while ((optchar = getopt(argc, argv, "s:pb")) != -1) {
    switch (optchar) {
    case 's':
      seed = (unsigned int) atoi(optarg);
      printf("Using user-provided seed: %u\n", seed);
      break;
    case 'b':
      benchmarkOnly = 1;
      break;
    case 'p':
      printFlag = 1;
      break;
    default:
      printf("Ignoring unrecognized option: %c\n", optchar);
      continue;
    }
  }

  // shift remaining arguments over
  int remaining_args = argc - optind;
  for (int i = 1; i <= remaining_args; ++i) {
    argv[i] = argv[i + optind - 1];
  }

  // check to make sure number of arguments is correct
  if (remaining_args != 2) {
    printf("Usage: %s [-p] [-b] [-s seed] <num_elements> <num_repeats>\n", argv[0]);
    printf("-p : print before/after arrays\n");
    printf("-b : run only the random/inverted timing test\n");
    exit(-1);
  }

  N = atoi(argv[1]);
  R = atoi(argv[2]);
  if (N < 1 || R < 1) {
    fprintf(stderr, "num_elements and num_repeats must be positive\n");
    return EXIT_FAILURE;
  }
  set_random_seed(seed);
  printf("Initial rand_r seed: %u; sort versions: %d; trials per input: %d\n",
         seed, kNumOfFunc, R);

  run_test_suite(0, printFlag, N, R, benchmarkOnly, testFunc, kNumOfFunc);

  return 0;
}

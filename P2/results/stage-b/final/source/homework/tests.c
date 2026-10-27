/**
 * Copyright (c) 2012 MIT License by 6.172 Staff
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


#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>
#include <assert.h>
#include <string.h>
#include <unistd.h>

#include "./fasttime.h"
#include "./tests.h"
#include "./sort_config.h"

// Call TEST_PASS() from your test cases to mark a test as successful
#define TEST_PASS() TEST_PASS_WITH_NAME(__func__, __LINE__)

#define TEST_PASS_WITH_NAME(name, line) \
    fprintf(stderr, " --> %s at line %d: PASS\n", (name), (line))

// Call TEST_FAIL from your test cases to mark a test as failed. TEST_FAIL
// should print a meaningful message with the reason that the test failed.
//
// Calling it is just like calling printf().
#define TEST_FAIL(failure_msg, args...) \
    TEST_FAIL_WITH_NAME(__func__, __LINE__, failure_msg, ##args)

#define TEST_FAIL_WITH_NAME(name, line, failure_msg, args...) do { \
    fprintf(stderr, " --> %s at line %d: FAIL\n    Reason:", (name), (line)); \
    fprintf(stderr, (failure_msg), ## args); \
    fprintf(stderr, "\n"); \
    exit(EXIT_FAILURE); \
} while (0)




/* Some global variables to make it easier to run individual tests. */
// static int test_verbose = 1 ;
static unsigned int randomSeed = 1;
static unsigned int initialSeed = 1;

void set_random_seed(unsigned int seed) {
  randomSeed = seed;
  initialSeed = seed;
}

static int compare_data(const void* lhs, const void* rhs) {
  data_t a = *(const data_t*) lhs;
  data_t b = *(const data_t*) rhs;
  return (a > b) - (a < b);
}

static inline void display_array(data_t* data, int N) {
  // display array
  for (int i = 0; i < N; i++) {
    printf("%d ", data[i]);
  }
  printf("\n");
}

static inline void copy_data(data_t* data, data_t* data_bcup, int N) {
  // copy data_bcup to data
  for (int i = 0 ; i < N ; i++) {
    *data++ = *data_bcup++;
  }
}

static inline int post_process(data_t* data, data_t* data_bcup, int N,
                               int printFlag, char* name, int begin, int end) {
  int result = 1;
  if (printFlag) {
    printf("%s: ", name);
    printf("Data after sort\n");
    display_array(data, N);
  }

  // check if the array is unchanged from data[0..begin-1]
  for (int i = 0 ; i < begin ; i++) {
    if (data[i] != data_bcup[i]) {
      printf("%s: ", name);
      TEST_FAIL("Array outside sort boundary changed!\n");
      result = 0;
      break;
    }
  }

  // check if sub-array is sorted
  for (int i = begin + 1 ; i < end + 1 ; i++) {
    if (data[i - 1] > data[i]) {
      printf("%s: ", name);
      TEST_FAIL("Arrays are sorted: NO!\n");
      result = 0;
      break;
    }
  }

  // check if the array is unchanged from data[end+1..N-1]
  for (int i = end + 1 ; i < N ; i++) {
    if (data[i] != data_bcup[i]) {
      printf("%s: ", name);
      TEST_FAIL("Array outside sort boundary changed!\n");
      result = 0;
      break;
    }
  }
  // Compare against a trusted reference, including elements outside the range.
  // This is outside the timed call to the candidate sorting function.
  data_t* expected = (data_t*) malloc(N * sizeof(data_t));
  if (expected == NULL) {
    TEST_FAIL("Not enough memory for reference check");
  }
  memcpy(expected, data_bcup, N * sizeof(data_t));
  qsort(expected + begin, end - begin + 1, sizeof(data_t), compare_data);
  for (int i = 0; i < N; i++) {
    if (data[i] != expected[i]) {
      TEST_FAIL("Reference mismatch at index %d: got %u, expected %u",
                i, data[i], expected[i]);
    }
  }
  free(expected);
  copy_data(data, data_bcup, N);
  return result;
}

static
void
init_data(data_t* data, int N, int randomPrefix, int invertedSuffix) {
  // initialize data with randomPrefix random numbers
  assert(randomPrefix <= N);
  /* random prefix */
  for (int i = 0; i < randomPrefix; i++) {
    data[i] = rand_r(&randomSeed) % RANGE;
  }
  /* sorted or inverted suffix - duplicates are OK */
  for (int i = randomPrefix; i < N; i++) {
    if (invertedSuffix) {
      data[i] = (N - i) % RANGE;         // inverted
    } else {
      data[i] = i % RANGE;             // sorted array
    }
  }
}


struct dataGenerator_t {
  void (*generate)(data_t*, int);
  char* name;
};

void all_random(data_t* data, int N) {
  init_data(data, N, N, 0);
}

void all_inverted(data_t* data, int N) {
  init_data(data, N, 0, 1 /* inverted */);
}

struct dataGenerator_t dataGen[] = {
  {all_random, "random"},
  {all_inverted, "inverted"},
};

static void test_correctness(int printFlag, int N, int R,
                             struct testFunc_t* testFunc, int numFunc) {
  fasttime_t time1, time2;
  data_t* data, *data_bcup;
  int success = 1;

  double* sum_time = (double*) alloca(numFunc * sizeof(double));
  for (int i = 0; i < numFunc; i++) {
    sum_time[i] = 0;
  }

  // allocate memory
  data = (data_t*) malloc(N * sizeof(data_t));
  data_bcup = (data_t*) malloc(N * sizeof(data_t));

  if (data == NULL || data_bcup == NULL) {
    printf("Error: not enough memory\n");
    free(data);
    free(data_bcup);
    exit(-1);
  }

  // Initialize elapsed time counters to 0.
  for (int k = 0; k < numFunc; k++) {
    sum_time[k] = 0;
  }

  // repeat for each array kind
  for (int gen = 0;
       gen < sizeof(dataGen) / sizeof(dataGen[0]);
       gen++) {
    for (int k = 0; k < numFunc; k++) {
      sum_time[k] = 0;
    }
    printf("Generating %s array of %d elements\n",
           dataGen[gen].name, N);
    // repeat for each trial
    for (int j = 0; j < R; j++) {
      // generate new data for each trial
      dataGen[gen].generate(data, N);

      if (printFlag) {
        printf("Data before sort\n");
        display_array(data, N);
      }
      uint64_t fingerprint = UINT64_C(14695981039346656037);
      for (int i = 0; i < N; i++) {
        data_bcup[i] = data[i];
        fingerprint = (fingerprint ^ data[i]) * UINT64_C(1099511628211);
      }

      for (int k = 0; k < numFunc; k++) {
        time1 = gettime();
        testFunc[k].func(data, 0, N - 1);
        time2 = gettime();
        testFunc[k].calls++;

        double elapsed = tdiff(time1, time2);
        sum_time[k] += elapsed;
        printf("TIMING input=%s trial=%d function=%s seconds=%.9f N=%d R=%d seed=%u fingerprint=%016llx\n",
               dataGen[gen].name, j + 1, testFunc[k].name, elapsed, N, R, initialSeed,
               (unsigned long long) fingerprint);
        success &= post_process(data, data_bcup, N, printFlag, testFunc[k].name, 0, N - 1);

        if (!success) {
          break;
        }
      }
    }

    if (success) {
      printf("Arrays are sorted: yes\n");
      TEST_PASS();
      // report average execution time over R runs.
      for (int k = 0; k < numFunc; k++) {
        double avgRuntime = R > 0 ? sum_time[k] / R : 0;
        printf("%s: Elapsed execution time: %.9f sec\n", testFunc[k].name, avgRuntime);
        printf("SUMMARY variant=%s input=%s N=%d R=%d seed=%u calls=%d mean_seconds=%.9f\n",
               testFunc[k].name, dataGen[gen].name, N, R, initialSeed, R, avgRuntime);
      }
    }
  }

  free(data);
  free(data_bcup);
  return;
}

static void test_zero_element(int printFlag, int N, int R,
                              struct testFunc_t* testFunc, int numFunc) {
  int success = 1;
  for (int i = 0; i < numFunc; i++) {
    data_t data[] = {0, 0, 0};
    testFunc[i].func(&data[1], 0, -1);
    testFunc[i].calls++;
    if (data[0] != 0 || data[1] != 0 || data[2] != 0) {
      printf("Error: %s failed to sort array with zero element\n",
             testFunc[i].name);
      success = 0;
    }
  }

  if (success) {
    TEST_PASS();
  } else {
    TEST_FAIL("Sorting array with zero element failed");
  }
}

static void test_one_element(int printFlag, int N, int R,
                             struct testFunc_t* testFunc, int numFunc) {
  int success = 1;
  for (int i = 0; i < numFunc; i++) {
    data_t data[] = {0, 1, 0};
    testFunc[i].func(&data[1], 0, 0);
    testFunc[i].calls++;
    if (data[0] != 0 || data[1] != 1 || data[2] != 0) {
      printf("Error: %s failed to sort array with one element\n",
             testFunc[i].name);
      success = 0;
    }
  }

  if (success) {
    TEST_PASS();
  } else {
    TEST_FAIL("Sorting array with one element failed");
  }
}

void test_subarray(int printFlag, int N, int R,
                   struct testFunc_t* testFunc, int numFunc) {
  data_t* data, *data_bcup;
  int success = 1;

  // allocate memory
  data = (data_t*) malloc(N * sizeof(data_t));
  data_bcup = (data_t*) malloc(N * sizeof(data_t));

  if (data == NULL || data_bcup == NULL) {
    printf("Error: not enough memory\n");
    free(data);
    free(data_bcup);
    exit(-1);
  }

  // initialize data with random numbers
  for (int i = 0; i < N; i++) {
    data[i] = rand_r(&randomSeed);
    data_bcup[i] = data[i];
  }
  if (printFlag) {
    printf("Data before sort\n");
    display_array(data, N);
  }
  int begin = rand_r(&randomSeed) % N;
  int end = N - 1 - begin;
  if (begin > end) {
    int temp = begin;
    begin = end;
    end = temp;
  }

  printf("Sorting subarray A[%d..%d]\n", begin, end);
  for (int i = 0; i < numFunc; i++) {
    testFunc[i].func(data, begin, end);
    testFunc[i].calls++;
    success &= post_process(data, data_bcup, N, printFlag, testFunc[i].name, begin, end);
  }

  if (success) {
    printf("Arrays are sorted: yes\n");
    TEST_PASS();
  } else {
    TEST_FAIL("Sorting subarray failed");
  }

  free(data);
  free(data_bcup);
  return;
}

static void test_patterns(int printFlag, int N, int R,
                          struct testFunc_t* testFunc, int numFunc) {
  const int sizes[] = {0, 1, 2, 3, 7, 8, 9, 15, 16, 17, 31, 32, 33,
                       63, 64, 65, 127, 128, 129, 257,
                       SORT_CUTOFF - 1, SORT_CUTOFF, SORT_CUTOFF + 1};
  unsigned int pattern_seed = 12345;
  int cases = 0;
  for (unsigned int s = 0; s < sizeof(sizes) / sizeof(sizes[0]); s++) {
    int length = sizes[s];
    for (int pattern = 0; pattern < 5; pattern++) {
      for (int offset = 0; offset <= 2; offset += 2) {
        int total = length + 5;
        data_t* data = malloc(total * sizeof(data_t));
        data_t* original = malloc(total * sizeof(data_t));
        if (data == NULL || original == NULL) TEST_FAIL("Pattern allocation failed");
        for (int j = 0; j < total; j++) data[j] = 0x12345678U;
        for (int j = 0; j < length; j++) {
          data_t value = 0;
          switch (pattern) {
          case 0: value = j; break;
          case 1: value = length - j; break;
          case 2: value = rand_r(&pattern_seed) % RANGE; break;
          case 3: value = j % 4; break;
          case 4: value = 42; break;
          }
          data[offset + j] = value;
        }
        memcpy(original, data, total * sizeof(data_t));
        for (int k = 0; k < numFunc; k++) {
          testFunc[k].func(data, offset, offset + length - 1);
          testFunc[k].calls++;
          post_process(data, original, total, 0, testFunc[k].name,
                       offset, offset + length - 1);
        }
        cases++;
        free(data);
        free(original);
      }
    }
  }
  for (int k = 0; k < numFunc; k++)
    printf("PATTERNS variant=%s cases=%d domain=0..2147483647\n", testFunc[k].name, cases);
  TEST_PASS();
}

test_case test_cases[] = {
  test_correctness,
  test_zero_element,
  test_one_element,
  test_patterns,
  // test_subarray,
  // ADD YOUR TEST CASES HERE
  NULL  // This marks the end of all test cases. Don't change this!
};

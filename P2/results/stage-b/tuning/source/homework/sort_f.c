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


#include "./util.h"
#include "./sort_config.h"

static inline void insertion_f(data_t* A, int p, int r) {
  for (int i = p + 1; i <= r; i++) {
    data_t value = A[i];
    int j = i;
    while (j > p && A[j - 1] > value) { A[j] = A[j - 1]; j--; }
    A[j] = value;
  }
}

static void merge_f(data_t* A, int p, int q, int r, data_t* left) {
  int n1 = q - p + 1;
  for (int i = 0; i < n1; i++) left[i] = A[p + i];
  int i = 0, j = q + 1, k = p;
  while (i < n1 && j <= r) {
    if (left[i] <= A[j]) A[k++] = left[i++];
    else A[k++] = A[j++];
  }
  while (i < n1) A[k++] = left[i++];
}

static void recursive_f(data_t* A, int p, int r, data_t* scratch) {
  if (p >= r) return;
  if (r - p + 1 <= SORT_CUTOFF) {
    insertion_f(A, p, r);
    return;
  }
  int q = (p + r) / 2;
  recursive_f(A, p, q, scratch);
  recursive_f(A, q + 1, r, scratch);
  merge_f(A, p, q, r, scratch);
}

void sort_f(data_t* A, int p, int r) {
  assert(A);
  if (p >= r) return;
  if (r - p + 1 <= SORT_CUTOFF) {
    insertion_f(A, p, r);
    return;
  }
  int n = r - p + 1;
  data_t* scratch = 0;
  mem_alloc(&scratch, n / 2 + n % 2);
  if (scratch == NULL) return;
  recursive_f(A, p, r, scratch);
  mem_free(&scratch);
}


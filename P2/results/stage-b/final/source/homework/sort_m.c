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

static inline void insertion_m(data_t* A, int p, int r) {
  for (int i = p + 1; i <= r; i++) {
    data_t value = A[i];
    int j = i;
    while (j > p && A[j - 1] > value) { A[j] = A[j - 1]; j--; }
    A[j] = value;
  }
}

static void merge_m(data_t* A, int p, int q, int r) {
  int n1 = q - p + 1;
  data_t* left = 0;
  mem_alloc(&left, n1);
  if (left == NULL) exit(EXIT_FAILURE);
  for (int i = 0; i < n1; i++) left[i] = A[p + i];
  int i = 0, j = q + 1, k = p;
  // While i<n1, j-k=n1-i>0: writing A[k] cannot overwrite unread A[j].
  while (i < n1 && j <= r) {
    if (left[i] <= A[j]) A[k++] = left[i++];
    else A[k++] = A[j++];
  }
  while (i < n1) A[k++] = left[i++];
  // If the left side ended first, k==j and the remaining right side stays put.
  mem_free(&left);
}

void sort_m(data_t* A, int p, int r) {
  assert(A);
  if (p >= r) return;
  if (r - p + 1 <= SORT_CUTOFF) {
    insertion_m(A, p, r);
    return;
  }
  int q = (p + r) / 2;
  sort_m(A, p, q);
  sort_m(A, q + 1, r);
  merge_m(A, p, q, r);
}


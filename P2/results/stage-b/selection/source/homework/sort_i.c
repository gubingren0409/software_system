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

// Local equivalents isolate inlining from the unchanged baseline util.c.
static inline void alloc_i(data_t** space, int size) {
  *space = malloc(sizeof(data_t) * size);
  if (*space == NULL) printf("out of memory...\n");
}

static inline void free_i(data_t** space) {
  free(*space);
  *space = 0;
}

static inline void copy_i(data_t* source, data_t* dest, int n) {
  assert(dest);
  assert(source);
  for (int i = 0; i < n; i++) dest[i] = source[i];
}

static inline void merge_i(data_t* A, int p, int q, int r) {
  assert(A);
  assert(p <= q && q + 1 <= r);
  int n1 = q - p + 1, n2 = r - q;
  data_t *left = 0, *right = 0;
  alloc_i(&left, n1 + 1);
  alloc_i(&right, n2 + 1);
  if (left == NULL || right == NULL) {
    free_i(&left);
    free_i(&right);
    return;
  }
  copy_i(A + p, left, n1);
  copy_i(A + q + 1, right, n2);
  left[n1] = UINT_MAX;
  right[n2] = UINT_MAX;
  int i = 0, j = 0;
  for (int k = p; k <= r; k++) {
    if (left[i] <= right[j]) A[k] = left[i++];
    else A[k] = right[j++];
  }
  free_i(&left);
  free_i(&right);
}

#if I_RECURSIVE_INLINE
#define I_RECURSION inline
#else
#define I_RECURSION
#endif

static I_RECURSION void recursive_i(data_t* A, int p, int r) {
  assert(A);
  if (p < r) {
    int q = (p + r) / 2;
    recursive_i(A, p, q);
    recursive_i(A, q + 1, r);
    merge_i(A, p, q, r);
  }
}

void sort_i(data_t* A, int p, int r) {
  recursive_i(A, p, r);
}


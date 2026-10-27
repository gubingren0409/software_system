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

static inline void alloc_p(data_t** space, int size) {
  *space = malloc(sizeof(data_t) * size);
  if (*space == NULL) printf("out of memory...\n");
}

static inline void free_p(data_t** space) {
  free(*space);
  *space = 0;
}

static inline void copy_p(data_t* source, data_t* dest, int n) {
  assert(dest);
  assert(source);
  data_t* end = source + n;
  while (source < end) *dest++ = *source++;
}

static inline void merge_p(data_t* A, int p, int q, int r) {
  assert(A);
  assert(p <= q && q + 1 <= r);
  int n1 = q - p + 1, n2 = r - q;
  data_t *left = 0, *right = 0;
  alloc_p(&left, n1 + 1);
  alloc_p(&right, n2 + 1);
  if (left == NULL || right == NULL) {
    free_p(&left);
    free_p(&right);
    return;
  }
  copy_p(A + p, left, n1);
  copy_p(A + q + 1, right, n2);
  left[n1] = UINT_MAX;
  right[n2] = UINT_MAX;
  data_t *l = left, *right_ptr = right, *out = A + p, *end = A + r + 1;
  while (out < end) {
    if (*l <= *right_ptr) *out++ = *l++;
    else *out++ = *right_ptr++;
  }
  free_p(&left);
  free_p(&right);
}

static inline void recursive_p(data_t* A, int p, int r) {
  assert(A);
  if (p < r) {
    int q = (p + r) / 2;
    recursive_p(A, p, q);
    recursive_p(A, q + 1, r);
    merge_p(A, p, q, r);
  }
}

void sort_p(data_t* A, int p, int r) {
  recursive_p(A, p, r);
}


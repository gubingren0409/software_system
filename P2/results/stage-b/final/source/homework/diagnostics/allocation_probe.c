// Diagnostic only: linker wrappers count scratch allocations inside one sort call.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../sort.h"

void* __real_malloc(size_t size);
void __real_free(void* pointer);
static int active;
static size_t allocations, releases, requested, live, peak;
static struct { void* pointer; size_t size; } slots[16];

void* __wrap_malloc(size_t size) {
  void* pointer = __real_malloc(size);
  if (active && pointer) {
    allocations++;
    requested += size;
    live += size;
    if (live > peak) peak = live;
    int index;
    for (index = 0; index < 16; index++) if (!slots[index].pointer) break;
    if (index == 16) abort();
    slots[index].pointer = pointer;
    slots[index].size = size;
  }
  return pointer;
}

void __wrap_free(void* pointer) {
  if (active && pointer) {
    int index;
    for (index = 0; index < 16; index++) if (slots[index].pointer == pointer) break;
    if (index == 16) abort();
    live -= slots[index].size;
    slots[index].pointer = NULL;
    releases++;
  }
  __real_free(pointer);
}

static int compare(const void* a, const void* b) {
  data_t x = *(const data_t*)a, y = *(const data_t*)b;
  return (x > y) - (x < y);
}

int main(void) {
  const int n = 131073, start = 3, total = n + 6;
  void (*functions[])(data_t*,int,int) = {sort_a,sort_i,sort_p,sort_c,sort_m,sort_f};
  const char* names[] = {"a","i","p","c","m","f"};
  data_t* original = malloc(total * sizeof(data_t));
  data_t* data = malloc(total * sizeof(data_t));
  data_t* expected = malloc(total * sizeof(data_t));
  if (!original || !data || !expected) return 1;
  unsigned int seed = 42;
  for (int i = 0; i < total; i++) original[i] = rand_r(&seed);
  memcpy(expected, original, total * sizeof(data_t));
  qsort(expected + start, n, sizeof(data_t), compare);
  for (int v = 0; v < 6; v++) {
    memcpy(data, original, total * sizeof(data_t));
    allocations = releases = requested = live = peak = 0;
    memset(slots, 0, sizeof(slots));
    active = 1;
    functions[v](data, start, start + n - 1);
    active = 0;
    if (live != 0 || allocations != releases || memcmp(data, expected, total * sizeof(data_t))) return 1;
    printf("{\"variant\":\"%s\",\"N\":%d,\"start\":%d,\"malloc_calls\":%zu,\"free_calls\":%zu,\"requested_bytes\":%zu,\"peak_live_bytes\":%zu,\"remaining_live_bytes\":%zu}\n",
           names[v], n, start, allocations, releases, requested, peak, live);
  }
  free(original);
  free(data);
  free(expected);
  return 0;
}

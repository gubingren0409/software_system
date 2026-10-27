// Deliberately wrong implementation used only in the driver rejection test.
#include "../util.h"
void sort_a(data_t* A, int p, int r) {
  for (int i = p; i <= r; i++) A[i] = 0;
}

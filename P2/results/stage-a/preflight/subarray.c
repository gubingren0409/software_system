#include "tests.h"
extern void sort_a(data_t*,int,int);
extern void test_subarray(int,int,int,struct testFunc_t*,int);
int main(void) { struct testFunc_t f={sort_a,"sort_a"}; set_random_seed(42); test_subarray(1,33,1,&f,1); return 0; }

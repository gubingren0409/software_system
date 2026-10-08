#define main reference_generator_program_main
#include "../code/working/reference_generator.c"
#undef main

int main(void) {
    int coordinates[16][2];
    const size_t count = sample_coordinates(coordinates, 16);
    for (size_t index = 0; index < count; ++index) {
        if (coordinates[index][0] < 0 || coordinates[index][0] >= MATRIX_N ||
            coordinates[index][1] < 0 || coordinates[index][1] >= MATRIX_N) {
            return 1;
        }
    }
    const size_t expected = MATRIX_N == 1 ? 1u : (MATRIX_N == 2 ? 4u : 16u);
    if (count != expected) {
        return 2;
    }
    printf("{\"n\":%d,\"sample_count\":%zu,\"all_in_range\":true}\n",
           MATRIX_N, count);
    return 0;
}

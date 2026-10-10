/* One-shot read-only diagnostic; modes is explicitly zero. No setters. */
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <sys/timex.h>

int main(void) {
    struct timex state = {0};
    state.modes = 0;
    errno = 0;
    int result = adjtimex(&state);
    if (result == -1) {
        fprintf(stderr, "adjtimex(modes=0): %s\n", strerror(errno));
        return 1;
    }
    printf("{\"schema\":\"read-only-adjtimex-v1\",\"requested_modes\":0,"
           "\"returned_modes\":%u,\"return_state\":%d,\"freq\":%ld,"
           "\"freq_unit\":\"scaled ppm (65536 units per ppm)\",\"freq_ppm\":%.12f,"
           "\"tick\":%ld,\"tick_unit\":\"microseconds\",\"status\":%d,"
           "\"offset\":%ld,\"offset_unit\":\"%s\",\"maxerror\":%ld,"
           "\"esterror\":%ld,\"maxerror_esterror_unit\":\"microseconds\","
           "\"tai\":%d,\"system_settings_modified\":false}\n",
           state.modes, result, state.freq, state.freq / 65536.0,
           state.tick, state.status, state.offset,
           (state.status & STA_NANO) ? "nanoseconds (STA_NANO)" : "microseconds",
           state.maxerror, state.esterror, state.tai);
    return 0;
}

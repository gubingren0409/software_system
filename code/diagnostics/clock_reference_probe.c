#define _GNU_SOURCE
#include <errno.h>
#include <inttypes.h>
#include <limits.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/syscall.h>
#include <sys/timex.h>
#include <time.h>
#include <unistd.h>

/* Diagnostic only: the matrix source and its timer are not modified. */
static int direct_syscall;
static int selected_cpu = -1;
static cpu_set_t original_affinity;

static int64_t read_ns(clockid_t id) {
    struct timespec t;
    int rc = direct_syscall ? (int)syscall(SYS_clock_gettime, id, &t) : clock_gettime(id, &t);
    if (rc || t.tv_sec < 0 || t.tv_sec > INT64_MAX / 1000000000 ||
        t.tv_nsec < 0 || t.tv_nsec >= 1000000000) {
        perror("clock_gettime");
        exit(70);
    }
    return (int64_t)t.tv_sec * 1000000000 + t.tv_nsec;
}

static int decimal(const char *s, uint64_t *value) {
    if (!s || !*s) return 0;
    uint64_t n = 0;
    for (; *s; s++) {
        if (*s < '0' || *s > '9' || n > (UINT64_MAX - (unsigned)(*s - '0')) / 10) return 0;
        n = n * 10 + (unsigned)(*s - '0');
    }
    *value = n;
    return 1;
}

static void prefix(uint64_t seq, const char *op) {
    printf("{\"schema\":\"native-clock-endpoint-v1\",\"pid\":%ld,\"seq\":%" PRIu64
           ",\"op\":\"%s\",\"path\":\"%s\",\"selected_cpu\":%d",
           (long)getpid(), seq, op, direct_syscall ? "syscall" : "libc", selected_cpu);
}

int main(void) {
    if (sched_getaffinity(0, sizeof(original_affinity), &original_affinity)) {
        perror("sched_getaffinity"); return 70;
    }
    prefix(0, "HELLO");
    printf(",\"allowed_cpus\":[");
    int separator = 0;
    for (int cpu = 0; cpu < CPU_SETSIZE; cpu++) if (CPU_ISSET(cpu, &original_affinity)) {
        printf("%s%d", separator++ ? "," : "", cpu);
    }
    struct timex tx;
    memset(&tx, 0, sizeof(tx)); /* modes=0: query only, never adjust the clock. */
    int state = adjtimex(&tx);
    printf("],\"adjtimex\":{\"modes\":0,\"returncode\":%d", state);
    if (state < 0) printf(",\"status\":\"unknown\",\"errno\":%d", errno);
    else printf(",\"freq\":%ld,\"freq_units\":\"scaled-ppm\",\"freq_ppm\":%.12f,"
                "\"tick\":%ld,\"tick_units\":\"microseconds\",\"status\":%d,"
                "\"offset\":%ld,\"offset_units\":\"%s\",\"maxerror\":%ld,"
                "\"esterror\":%ld,\"error_units\":\"microseconds\"",
                tx.freq, tx.freq / 65536.0, tx.tick, tx.status, tx.offset,
                (tx.status & STA_NANO) ? "nanoseconds" : "microseconds", tx.maxerror, tx.esterror);
    printf("}}\n"); fflush(stdout);
    char line[160];
    uint64_t previous = 0;
    while (fgets(line, sizeof(line), stdin)) {
        if (!strchr(line, '\n')) return 64;
        char *save = NULL, *op = strtok_r(line, " \n", &save);
        char *seq_s = strtok_r(NULL, " \n", &save);
        uint64_t seq;
        if (!decimal(seq_s, &seq) || seq != previous + 1 || previous == UINT64_MAX) return 64;
        previous = seq;
        if (!strcmp(op, "MODE")) {
            char *path = strtok_r(NULL, " \n", &save), *cpu_s = strtok_r(NULL, " \n", &save);
            uint64_t cpu = 0;
            if (!path || !cpu_s || (strcmp(path,"libc") && strcmp(path,"syscall")) ||
                (strcmp(cpu_s,"-1") && (!decimal(cpu_s,&cpu) || cpu >= CPU_SETSIZE ||
                    !CPU_ISSET((int)cpu,&original_affinity))) || strtok_r(NULL," \n",&save)) return 64;
            selected_cpu = !strcmp(cpu_s,"-1") ? -1 : (int)cpu;
            cpu_set_t mask = original_affinity;
            if (selected_cpu >= 0) { CPU_ZERO(&mask); CPU_SET(selected_cpu,&mask); }
            if (sched_setaffinity(0,sizeof(mask),&mask)) { perror("sched_setaffinity"); return 70; }
            direct_syscall = !strcmp(path,"syscall");
            prefix(seq,op); printf("}\n");
        } else if (!strcmp(op,"READ")) {
            if (strtok_r(NULL," \n",&save)) return 64;
            int cpu_before = sched_getcpu();
            int64_t m1 = read_ns(CLOCK_MONOTONIC);
            int64_t r = read_ns(CLOCK_MONOTONIC_RAW);
            int64_t m2 = read_ns(CLOCK_MONOTONIC);
            int64_t rt = read_ns(CLOCK_REALTIME);
            int64_t bt = read_ns(CLOCK_BOOTTIME);
            int cpu_after = sched_getcpu();
            prefix(seq,op);
            printf(",\"m1_ns\":%" PRId64 ",\"raw_ns\":%" PRId64 ",\"m2_ns\":%" PRId64
                   ",\"realtime_ns\":%" PRId64 ",\"boottime_ns\":%" PRId64
                   ",\"cpu_before\":%d,\"cpu_after\":%d}\n",m1,r,m2,rt,bt,cpu_before,cpu_after);
        } else if (!strcmp(op,"WAIT")) {
            char *kind = strtok_r(NULL," \n",&save);
            if (!kind || (strcmp(kind,"idle") && strcmp(kind,"busy")) || strtok_r(NULL," \n",&save)) return 64;
            volatile uint64_t work = UINT64_C(0x123456789abcdef);
            if (!strcmp(kind,"idle")) {
                struct timespec delay = {3,0};
                while (nanosleep(&delay,&delay)) if (errno != EINTR) { perror("nanosleep"); return 70; }
            } else {
                int64_t start = read_ns(CLOCK_MONOTONIC);
                do {
                    for (int i=0;i<16384;i++) work = (work ^ (work >> 13)) * UINT64_C(6364136223846793005) + 1;
                } while (read_ns(CLOCK_MONOTONIC)-start < INT64_C(3000000000));
            }
            prefix(seq,op); printf(",\"workload\":\"%s\",\"work_checksum\":%" PRIu64 "}\n",kind,work);
        } else if (!strcmp(op,"QUIT")) {
            if (strtok_r(NULL," \n",&save)) return 64;
            prefix(seq,op); printf("}\n"); fflush(stdout); return 0;
        } else return 64;
        fflush(stdout); /* Every response survives a later timeout. */
    }
    return ferror(stdin) ? 74 : 0;
}

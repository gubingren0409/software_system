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

/* Independent diagnostic. WORK never reads a clock or calls sleep. */
static int direct_syscall;
static int selected_cpu = -1;
static cpu_set_t original_affinity;

static int64_t read_ns(clockid_t id) {
    struct timespec t;
    int rc = direct_syscall ? (int)syscall(SYS_clock_gettime, id, &t) : clock_gettime(id, &t);
    if (rc || t.tv_sec < 0 || t.tv_nsec < 0 || t.tv_nsec >= 1000000000 ||
        (uint64_t)t.tv_sec > ((uint64_t)INT64_MAX - (uint64_t)t.tv_nsec) / 1000000000) {
        perror("clock_gettime"); exit(70);
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
    *value = n; return 1;
}

static void prefix(uint64_t seq, const char *op) {
    printf("{\"schema\":\"fixed-work-clock-endpoint-v1\",\"pid\":%ld,\"seq\":%" PRIu64
           ",\"op\":\"%s\",\"path\":\"%s\",\"selected_cpu\":%d",
           (long)getpid(), seq, op, direct_syscall ? "syscall" : "libc", selected_cpu);
}

static void timex_metadata(void) {
    struct timex tx;
    memset(&tx, 0, sizeof(tx)); /* modes=0: read only. */
    int state = adjtimex(&tx), saved_errno = errno;
    printf(",\"adjtimex\":{\"modes\":0,\"returncode\":%d", state);
    if (state < 0) printf(",\"status\":\"unknown\",\"errno\":%d", saved_errno);
    else printf(",\"freq\":%ld,\"freq_units\":\"scaled-ppm\",\"freq_ppm\":%.12f,"
                "\"tick\":%ld,\"tick_units\":\"microseconds\",\"status\":%d,"
                "\"offset\":%ld,\"offset_units\":\"%s\",\"maxerror\":%ld,"
                "\"esterror\":%ld,\"error_units\":\"microseconds\"",
                tx.freq, tx.freq / 65536.0, tx.tick, tx.status, tx.offset,
                (tx.status & STA_NANO) ? "nanoseconds" : "microseconds", tx.maxerror, tx.esterror);
    printf("}");
}

static void file_metadata(const char *key, const char *path) {
    char text[256];
    FILE *f = fopen(path, "r");
    if (!f || !fgets(text, sizeof(text), f)) {
        printf(",\"%s\":\"unknown\"", key);
    } else {
        text[strcspn(text, "\r\n")] = 0;
        printf(",\"%s\":\"", key);
        for (const unsigned char *p = (unsigned char *)text; *p; p++) {
            if (*p == '"' || *p == '\\') putchar('\\');
            if (*p >= 32) putchar(*p);
        }
        putchar('"');
    }
    if (f) fclose(f);
}

int main(void) {
    if (sched_getaffinity(0, sizeof(original_affinity), &original_affinity)) {
        perror("sched_getaffinity"); return 70;
    }
    prefix(0, "HELLO"); printf(",\"allowed_cpus\":[");
    int separator = 0;
    for (int cpu = 0; cpu < CPU_SETSIZE; cpu++) if (CPU_ISSET(cpu, &original_affinity))
        printf("%s%d", separator++ ? "," : "", cpu);
    printf("]"); timex_metadata(); printf("}\n"); fflush(stdout);
    char line[160]; uint64_t previous = 0;
    while (fgets(line, sizeof(line), stdin)) {
        if (!strchr(line, '\n')) return 64;
        char *save = NULL, *op = strtok_r(line, " \n", &save), *seq_s = strtok_r(NULL, " \n", &save);
        uint64_t seq;
        if (!decimal(seq_s, &seq) || previous == UINT64_MAX || seq != previous + 1) return 64;
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
            direct_syscall = !strcmp(path,"syscall"); prefix(seq,op); printf("}\n");
        } else if (!strcmp(op,"READ")) {
            if (strtok_r(NULL," \n",&save)) return 64;
            int cpu_before = sched_getcpu();
            int64_t m1 = read_ns(CLOCK_MONOTONIC);
            int64_t r1 = read_ns(CLOCK_MONOTONIC_RAW);
            int64_t m = read_ns(CLOCK_MONOTONIC);
            int64_t r2 = read_ns(CLOCK_MONOTONIC_RAW);
            int64_t m2 = read_ns(CLOCK_MONOTONIC);
            int64_t rt = read_ns(CLOCK_REALTIME), bt = read_ns(CLOCK_BOOTTIME);
            int cpu_after = sched_getcpu();
            prefix(seq,op);
            printf(",\"m1_ns\":%" PRId64 ",\"raw1_ns\":%" PRId64 ",\"monotonic_ns\":%" PRId64
                   ",\"raw2_ns\":%" PRId64 ",\"m2_ns\":%" PRId64 ",\"realtime_ns\":%" PRId64
                   ",\"boottime_ns\":%" PRId64 ",\"cpu_before\":%d,\"cpu_after\":%d",
                   m1,r1,m,r2,m2,rt,bt,cpu_before,cpu_after);
            timex_metadata();
            file_metadata("boot_id","/proc/sys/kernel/random/boot_id");
            file_metadata("uptime","/proc/uptime");
            file_metadata("clocksource","/sys/devices/system/clocksource/clocksource0/current_clocksource");
            printf("}\n");
        } else if (!strcmp(op,"WORK")) {
            uint64_t updates;
            if (!decimal(strtok_r(NULL," \n",&save),&updates) ||
                (updates != UINT64_C(1000000000) && updates != UINT64_C(10000000000)) ||
                strtok_r(NULL," \n",&save)) return 64;
            volatile uint64_t work = UINT64_C(0x123456789abcdef);
            for (uint64_t i=0; i<updates; i++)
                work = (work ^ (work >> 13)) * UINT64_C(6364136223846793005) + 1;
            prefix(seq,op);
            printf(",\"executed_updates\":%" PRIu64 ",\"work_checksum\":%" PRIu64 "}\n",updates,work);
        } else if (!strcmp(op,"QUIT")) {
            if (strtok_r(NULL," \n",&save)) return 64;
            prefix(seq,op); printf("}\n"); fflush(stdout); return 0;
        } else return 64;
        fflush(stdout);
    }
    return ferror(stdin) ? 74 : 0;
}

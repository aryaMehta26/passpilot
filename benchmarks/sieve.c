#include "bench.h"
#define N 100000000
static unsigned char composite[N + 1];
int main(void) {
    for (long i = 2; i * i <= N; i++)
        if (!composite[i]) for (long j = i * i; j <= N; j += i) composite[j] = 1;
    uint64_t count = 0, sum = 0;
    for (long i = 2; i <= N; i++) if (!composite[i]) { count++; sum += (uint64_t)i; }
    report_u64(count * 1000003ull ^ sum); return 0;
}

#include "bench.h"
#define N 8000000
#define BINS 256
static unsigned char data[N];
static uint32_t hist[BINS];
int main(void) {
    for (int i = 0; i < N; i++) data[i] = (unsigned char)(lcg() >> 24);
    for (int r = 0; r < 36; r++) for (int i = 0; i < N; i++) hist[data[i]]++;
    uint64_t h = 0; for (int b = 0; b < BINS; b++) h = h * 31 + hist[b];
    report_u64(h); return 0;
}

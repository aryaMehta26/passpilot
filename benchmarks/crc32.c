#include "bench.h"
#define N (6 * 1024 * 1024)
static unsigned char buf[N];
static uint32_t crc_bitwise(const unsigned char *p, int n) {
    uint32_t c = 0xffffffffu;
    for (int i = 0; i < n; i++) {
        c ^= p[i];
        for (int k = 0; k < 8; k++) c = (c >> 1) ^ (0xedb88320u & (0u - (c & 1u)));
    }
    return ~c;
}
int main(void) {
    for (int i = 0; i < N; i++) buf[i] = (unsigned char)(lcg() >> 24);
    report_u64(crc_bitwise(buf, N)); return 0;
}

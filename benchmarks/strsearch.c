#include "bench.h"
#define N (4 * 1024 * 1024)
#define P 12
static char text[N], pat[P];
int main(void) {
    for (int i = 0; i < N; i++) text[i] = 'a' + lcg_below(3);
    for (int i = 0; i < P; i++) pat[i] = 'a' + lcg_below(3);
    uint64_t hits = 0, posh = 0;
    for (int r = 0; r < 3; r++)
        for (int i = 0; i + P <= N; i++) {
            int k = 0;
            while (k < P && text[i + k] == pat[k]) k++;
            if (k == P) { hits++; posh = posh * 31 + (uint64_t)i; }
        }
    report_u64(hits ^ posh); return 0;
}

#include "bench.h"
#define N 1500000
static int v[N];
static void qs(int *x, int lo, int hi) {
    while (lo < hi) {
        int p = x[(lo + hi) / 2], i = lo, j = hi;
        while (i <= j) {
            while (x[i] < p) i++;
            while (x[j] > p) j--;
            if (i <= j) { int t = x[i]; x[i] = x[j]; x[j] = t; i++; j--; }
        }
        if (j - lo < hi - i) { qs(x, lo, j); lo = i; } else { qs(x, i, hi); hi = j; }
    }
}
int main(void) {
    for (int i = 0; i < N; i++) v[i] = (int)(lcg() & 0x7fffffff);
    qs(v, 0, N - 1);
    uint64_t h = 1469598103934665603ull;
    for (int i = 0; i < N; i += 97) h = (h ^ (uint64_t)v[i]) * 1099511628211ull;
    report_u64(h); return 0;
}

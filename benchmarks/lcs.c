#include "bench.h"
#define N 3000
static char a[N], b[N];
static int prev[N + 1], cur[N + 1];
int main(void) {
    for (int i = 0; i < N; i++) { a[i] = 'a' + lcg_below(4); b[i] = 'a' + lcg_below(4); }
    for (int i = 1; i <= N; i++) {
        for (int j = 1; j <= N; j++) {
            if (a[i - 1] == b[j - 1]) cur[j] = prev[j - 1] + 1;
            else cur[j] = prev[j] > cur[j - 1] ? prev[j] : cur[j - 1];
        }
        for (int j = 0; j <= N; j++) prev[j] = cur[j];
    }
    report_u64((uint64_t)prev[N]); return 0;
}

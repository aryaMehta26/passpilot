#include "bench.h"
#define N 400
#define STEPS 1500
static double a[N][N], b[N][N];
int main(void) {
    for (int i = 0; i < N; i++) for (int j = 0; j < N; j++) a[i][j] = lcg_unit();
    for (int t = 0; t < STEPS; t++) {
        for (int i = 1; i < N - 1; i++) for (int j = 1; j < N - 1; j++)
            b[i][j] = 0.2 * (a[i][j] + a[i - 1][j] + a[i + 1][j] + a[i][j - 1] + a[i][j + 1]);
        for (int i = 1; i < N - 1; i++) for (int j = 1; j < N - 1; j++) a[i][j] = b[i][j];
    }
    double s = 0; for (int i = 0; i < N; i++) for (int j = 0; j < N; j++) s += a[i][j];
    report_f64(s); return 0;
}

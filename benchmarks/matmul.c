#include "bench.h"
#define N 220
static double A[N][N], B[N][N], C[N][N];
int main(void) {
    for (int i = 0; i < N; i++) for (int j = 0; j < N; j++) { A[i][j] = lcg_unit(); B[i][j] = lcg_unit(); }
    for (int i = 0; i < N; i++)
        for (int j = 0; j < N; j++) {
            double s = 0;
            for (int k = 0; k < N; k++) s += A[i][k] * B[k][j];
            C[i][j] = s;
        }
    double t = 0; for (int i = 0; i < N; i++) for (int j = 0; j < N; j++) t += C[i][j];
    report_f64(t); return 0;
}

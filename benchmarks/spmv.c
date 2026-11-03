#include "bench.h"
#define ROWS 60000
#define NNZ_PER_ROW 16
#define ITERS 30
static int col[ROWS * NNZ_PER_ROW], rowptr[ROWS + 1];
static double val[ROWS * NNZ_PER_ROW], x[ROWS], y[ROWS];
int main(void) {
    for (int r = 0; r <= ROWS; r++) rowptr[r] = r * NNZ_PER_ROW;
    for (int k = 0; k < ROWS * NNZ_PER_ROW; k++) { col[k] = lcg_below(ROWS); val[k] = lcg_unit(); }
    for (int i = 0; i < ROWS; i++) x[i] = lcg_unit();
    for (int it = 0; it < ITERS; it++) {
        for (int r = 0; r < ROWS; r++) {
            double s = 0;
            for (int k = rowptr[r]; k < rowptr[r + 1]; k++) s += val[k] * x[col[k]];
            y[r] = s;
        }
        double norm = 0; for (int i = 0; i < ROWS; i++) norm += y[i];
        for (int i = 0; i < ROWS; i++) x[i] = y[i] / norm;
    }
    double t = 0; for (int i = 0; i < ROWS; i++) t += x[i] * (i % 7);
    report_f64(t); return 0;
}

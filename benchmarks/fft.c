#include "bench.h"
#include <math.h>
#define LOGN 16
#define N (1 << LOGN)
static double re[N], im[N];
static void fft(double *xr, double *xi) {
    for (int i = 1, j = 0; i < N; i++) {
        int bit = N >> 1;
        for (; j & bit; bit >>= 1) j ^= bit;
        j ^= bit;
        if (i < j) { double t = xr[i]; xr[i] = xr[j]; xr[j] = t; t = xi[i]; xi[i] = xi[j]; xi[j] = t; }
    }
    for (int len = 2; len <= N; len <<= 1) {
        double ang = -2 * M_PI / len, wr = cos(ang), wi = sin(ang);
        for (int i = 0; i < N; i += len) {
            double cr = 1, ci = 0;
            for (int k = 0; k < len / 2; k++) {
                double ur = xr[i + k], ui = xi[i + k];
                double vr = xr[i + k + len / 2] * cr - xi[i + k + len / 2] * ci;
                double vi = xr[i + k + len / 2] * ci + xi[i + k + len / 2] * cr;
                xr[i + k] = ur + vr; xi[i + k] = ui + vi;
                xr[i + k + len / 2] = ur - vr; xi[i + k + len / 2] = ui - vi;
                double t = cr * wr - ci * wi; ci = cr * wi + ci * wr; cr = t;
            }
        }
    }
}
int main(void) {
    for (int i = 0; i < N; i++) { re[i] = lcg_unit(); im[i] = 0; }
    for (int r = 0; r < 12; r++) { fft(re, im); for (int i = 0; i < N; i++) { re[i] /= 256.0; im[i] /= 256.0; } }
    double s = 0; for (int i = 0; i < N; i += 13) s += re[i] + im[i];
    report_f64(s); return 0;
}

#include "bench.h"
#include <math.h>
#define NB 400
#define STEPS 40
static double px[NB], py[NB], pz[NB], vx[NB], vy[NB], vz[NB], m[NB];
int main(void) {
    for (int i = 0; i < NB; i++) { px[i] = lcg_unit(); py[i] = lcg_unit(); pz[i] = lcg_unit(); m[i] = 0.5 + lcg_unit(); vx[i] = vy[i] = vz[i] = 0; }
    for (int s = 0; s < STEPS; s++) {
        for (int i = 0; i < NB; i++) {
            double ax = 0, ay = 0, az = 0;
            for (int j = 0; j < NB; j++) {
                double dx = px[j] - px[i], dy = py[j] - py[i], dz = pz[j] - pz[i];
                double d2 = dx * dx + dy * dy + dz * dz + 1e-3;
                double inv = m[j] / (d2 * sqrt(d2));
                ax += dx * inv; ay += dy * inv; az += dz * inv;
            }
            vx[i] += 1e-4 * ax; vy[i] += 1e-4 * ay; vz[i] += 1e-4 * az;
        }
        for (int i = 0; i < NB; i++) { px[i] += 1e-4 * vx[i]; py[i] += 1e-4 * vy[i]; pz[i] += 1e-4 * vz[i]; }
    }
    double e = 0; for (int i = 0; i < NB; i++) e += m[i] * (vx[i] * vx[i] + vy[i] * vy[i] + vz[i] * vz[i]);
    report_f64(e); return 0;
}

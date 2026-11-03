#include "bench.h"
#define H 512
#define W 512
#define K 5
static float img[H][W], out[H][W], ker[K][K];
int main(void) {
    for (int i = 0; i < H; i++) for (int j = 0; j < W; j++) img[i][j] = (float)lcg_unit();
    for (int i = 0; i < K; i++) for (int j = 0; j < K; j++) ker[i][j] = (float)lcg_unit() / (K * K);
    for (int r = 0; r < 200; r++)
        for (int i = K / 2; i < H - K / 2; i++)
            for (int j = K / 2; j < W - K / 2; j++) {
                float s = 0;
                for (int a = 0; a < K; a++) for (int b = 0; b < K; b++) s += img[i + a - K / 2][j + b - K / 2] * ker[a][b];
                out[i][j] += s;
            }
    double t = 0; for (int i = 0; i < H; i++) for (int j = 0; j < W; j++) t += out[i][j];
    report_f64(t); return 0;
}

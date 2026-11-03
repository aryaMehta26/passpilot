/* Shared helpers: deterministic inputs and a checksum the harness compares across builds. */
#ifndef BENCH_H
#define BENCH_H
#include <stdint.h>
#include <stdio.h>

static uint32_t bench_seed = 12345u;
static inline uint32_t lcg(void) { bench_seed = bench_seed * 1664525u + 1013904223u; return bench_seed; }
/* Low bits of a power-of-two LCG have tiny periods, so draw small ranges from the high bits. */
static inline uint32_t lcg_below(uint32_t k) { return (lcg() >> 16) % k; }
static inline double lcg_unit(void) { return (lcg() >> 8) * (1.0 / 16777216.0); }

static inline void report_u64(uint64_t h) { printf("checksum %llu\n", (unsigned long long)h); }
static inline void report_f64(double x) { printf("checksum %.6e\n", x); }
#endif

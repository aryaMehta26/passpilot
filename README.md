<p align="center"><img src="docs/assets/header.svg" alt="PassPilot: AI agents that tune LLVM pipelines from compiler feedback" width="100%"></p>

<p align="center">
  <a href="https://github.com/aryaMehta26/passpilot/actions/workflows/ci.yml"><img src="https://github.com/aryaMehta26/passpilot/actions/workflows/ci.yml/badge.svg" alt="tests"></a>
  <img src="https://img.shields.io/badge/LLVM-23-262D3A?logo=llvm&logoColor=white" alt="LLVM 23">
  <img src="https://img.shields.io/badge/C%2B%2B-pass%20plugin-00599C?logo=cplusplus&logoColor=white" alt="C++ pass plugin">
  <img src="https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white" alt="Python 3.12">
  <img src="https://img.shields.io/badge/agent-Llama%203.1%20(local)-76B900" alt="local LLM agent">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-blue" alt="Apache 2.0"></a>
</p>

**PassPilot asks one question: can an AI agent read what the compiler tells it and pick a better optimization pipeline than `clang -O3`?** It compiles real C programs through LLVM under candidate pass pipelines, measures runtime, compile time, code size and correctness, and pits an LLM agent against random search, a genetic algorithm and a learned cost model under the same budget.

[Results](#results) · [How it works](#how-it-works) · [The agent loop](#the-agent-loop) · [Run it](#run-it) · [What I learned](#what-i-learned)

## The 30-second version

`-O3` is one fixed recipe of about a hundred LLVM passes, tuned to be good on average. For any single program, a different order or mix of passes can be faster. Finding it is a search problem: the space of pass sequences is enormous, and each guess costs a compile and a timed run.

PassPilot treats that as an agent problem. Every step, the agent sees:

- the C source and **IR features** pulled out by a C++ LLVM pass plugin (loops, loop depth, loads/stores, vector instructions)
- what it already tried: **runtime, speedup vs `-O3`, failures**
- **LLVM's own missed-optimization remarks**, e.g. *"loop not vectorized: call instruction cannot be vectorized"*

and proposes the next pipeline as JSON. A strict interface validates it, repairs or retries bad replies, and falls back to mutating the best pipeline if the model keeps failing, so no evaluation is ever wasted.

| | |
|---|---|
| 🧪 Benchmarks | **12** C kernels (matmul, conv2d, stencil, FFT, n-body, SpMV, quicksort, sieve, CRC32, LCS, histogram, string search) |
| 🔧 Pass catalog | **48** actions: 45 individual LLVM passes + `O1`/`O2`/`O3` as building blocks |
| 🔁 Pipelines compiled, run and checked | **1,200** (4 methods × 12 benchmarks × 25) |
| 🎯 Best result | **1.25× faster than `-O3`** (crc32) · 1.13× (conv2d) · 1.12× (sieve) |
| 🤖 Agent interface | **340** LLM calls · **0** invalid replies · **0** fallbacks · 40 duplicate proposals caught and retried |
| 📈 Cost model on unseen programs | **0.43** Spearman rank correlation · top pick within 5% of the best on **8 / 12** |
| ✅ Tests | **27** (24 unit + 3 LLVM integration) |

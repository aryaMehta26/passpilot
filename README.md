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

## Results

Every method got the same budget: **25 pipelines per benchmark**. Each method's best pipeline was then **re-measured 10 times side by side with `-O3`**, so the speedups below compare like with like.

<p align="center"><img src="docs/img/speedup_vs_o3.png" alt="Speedup over clang -O3 per benchmark and method" width="100%"></p>

| Benchmark | Random | Genetic | **LLM agent** | Cost model |
|:--|--:|--:|--:|--:|
| conv2d | 1.129 | 1.128 | 0.997 | 1.135 |
| crc32 | 1.253 | 1.248 | **1.228** | 1.240 |
| fft | 0.994 | 0.996 | 0.993 | 0.994 |
| histogram | 1.011 | 1.013 | **1.017** | 1.025 |
| lcs | 1.014 | 1.011 | 0.991 | 1.004 |
| matmul | 0.990 | 0.994 | 0.994 | 0.988 |
| nbody | 0.995 | 1.004 | 1.002 | 0.998 |
| quicksort | 1.032 | 1.003 | **1.042** | 0.983 |
| sieve | 1.067 | 1.108 | **1.115** | 1.091 |
| spmv | 0.981 | 1.004 | 0.991 | 0.998 |
| stencil | 1.013 | 1.004 | 1.010 | 1.006 |
| strsearch | 1.020 | 1.014 | 1.006 | 0.960 |
| **geomean** | **1.039** | **1.041** | **1.030** | **1.032** |

<sub>Speedup over `clang -O3` (higher is better). Apple M4, LLVM 23.1.4, codegen fixed at `llc -O2` so only the IR pipeline differs. Raw data: [`data/results.csv`](data/results.csv), every evaluation: [`data/evaluations.csv`](data/evaluations.csv).</sub>

**What the numbers say, honestly:**

- **-O3 is hard to beat on regular, vectorizable loops.** fft, matmul, nbody and spmv all land within about 1% of it, whatever the method.
- **The big wins come from not using O3.** crc32's best pipelines are built on `O1`, not `O3`: the extra `O3` transformations make its bit-by-bit loop slower. Every method found this, worth **1.25×**.
- **The agent wins where reasoning helps.** On quicksort it found a 5-pass pipeline, `loop-rotate licm indvars sroa instcombine`, that beats `-O3` by **4%** while compiling faster. On sieve it reached **1.12×** by adding unrolling after `O3`, at **2.9×** the compile time. That trade-off is the kind of thing the report is meant to surface.
- **A local 8B model doesn't beat simple search on average.** Random search and the GA reach a slightly higher geomean (1.04 vs 1.03). That matches published autotuning work: with a cheap evaluator, random search is a strong baseline. The agent's value here is **reliability**: it never lost to `-O3` by more than 2%, and every proposal came with a reason you can read.

<p align="center">
  <img src="docs/img/convergence.png" width="49%" alt="Best-so-far speedup by number of pipelines evaluated">
  <img src="docs/img/compile_tradeoff.png" width="49%" alt="Runtime speedup vs compile time">
</p>

## How it works

```mermaid
flowchart LR
    subgraph Programs["12 C benchmarks"]
        SRC[kernel.c<br/>deterministic input<br/>+ checksum]
    end

    subgraph LLVM["LLVM 23 toolchain"]
        FE[clang -O0<br/>no optnone] --> BC[(base .bc)]
        BC --> OPT[opt -passes=…]
        OPT --> LLC[llc -O2] --> LINK[link + sign]
        BC --> PLUG[IRFeatures<br/>C++ pass plugin]
        BC --> REM[missed-opt<br/>remarks]
    end

    subgraph Search["Search methods (same budget)"]
        RS[random search]
        GA[genetic algorithm]
        AG[LLM agent]
        CM[XGBoost cost model<br/>ranks 3,000 candidates]
    end

    EV{{Evaluator<br/>budget · cache · log}}
    RUN[run + time<br/>warm-up, min of 3]
    CHK{output ==<br/>-O0 output?}

    SRC --> FE
    RS & GA & AG & CM -->|pipeline| EV --> OPT
    LINK --> RUN --> CHK
    CHK -- yes --> SCORE[runtime · compile time · size]
    CHK -- no --> BAD[score = ∞]
    SCORE & BAD --> EV
    PLUG -.IR features.-> AG & CM
    REM -.compiler feedback.-> AG
    EV --> DATA[(evaluations.csv<br/>results.csv<br/>summary.json)]
```

Every candidate goes through the same path, so the **only** difference between two runs is the IR pipeline:

1. `clang -O0 -Xclang -disable-O0-optnone` → unoptimized bitcode, built once per benchmark
2. `opt -passes=<candidate>` → optimized bitcode (loop passes are nested in the right adaptors automatically)
3. `llc -O2` → object file → linked, signed binary
4. one untimed warm-up run, then the minimum of 3 timed runs
5. the program's checksum must match the `-O0` build, or the candidate scores ∞

## The agent loop

```mermaid
sequenceDiagram
    participant A as LLM agent (Llama 3.1, local)
    participant I as JSON interface
    participant E as Evaluator
    participant C as LLVM

    loop until 25 pipelines are spent
        A->>I: {"passes": [...], "reason": "..."}
        alt invalid JSON / unknown pass / already tried
            I-->>A: error, try again (max 2 retries)
        else model keeps failing
            I->>E: fallback: mutate the best pipeline
        else valid
            I->>E: pipeline
        end
        E->>C: compile · run · check output
        C-->>E: runtime, compile time, size, correct?
        E->>C: opt -pass-remarks-missed
        C-->>A: history table + missed-optimization remarks
    end
```

A real step from the quicksort run:

> **Remarks:** `loop not vectorized: call instruction cannot be vectorized (x3)` …
> **Agent:** `loop-rotate licm indvars sroa instcombine`, *"Apply loop rotation to simplify the loop structure, followed by LICM and indvars"*
> **Result:** 0.229 s vs 0.240 s at `-O3`: **1.04× faster**, with a fraction of `-O3`'s passes.

## The cost model

`IRFeatures` (a C++ pass plugin, [`plugin/IRFeatures.cpp`](plugin/IRFeatures.cpp)) turns each program into numbers: functions, loops, innermost loops, max loop depth, instructions inside loops, loads, stores, GEPs, PHIs, calls, FP and vector instructions. Each pipeline is encoded as per-pass counts plus where each pass first appears.

An XGBoost regressor predicts `log(speedup vs -O3)` and is tested **leave-one-benchmark-out**: the model scoring conv2d has never seen a conv2d measurement.

| Held-out metric | Result |
|---|---|
| Mean Spearman rank correlation | **0.43** (best: spmv 0.81, conv2d 0.71) |
| Top-ranked pipeline within 5% of the true best | **8 of 12** benchmarks |

Cost-model-guided search then scores 3,000 candidates for free and spends the real budget on the top 25.

## What I learned

Four bugs I hit along the way, each now with a fix (and most with a test):

1. **Low-bit LCG randomness.** The first LCS benchmark printed a checksum of `0`. The low 2 bits of a power-of-two LCG repeat every 4 calls, so the two "random" strings never shared a letter. Small ranges are now drawn from the high bits.
2. **macOS kills unsigned binaries.** Every candidate died with SIGKILL. Homebrew's clang left arm64 binaries unsigned; linking through the system driver signs them.
3. **The first run lies.** A freshly linked binary's first launch pays for code-signature checks, which made a 0.055 s kernel look like 0.19 s, and the early-stop rule then recorded that cold time. Every binary now gets an untimed warm-up run, and early stopping needs two slow timed runs.
4. **Search from zero can't reach -O3 in 25 tries.** Random pass orders lost 5× on conv2d because rebuilding O3's vectorization from single passes is very unlikely. Adding `O1`/`O2`/`O3` as macro-actions (as CompilerGym does) lets search build *on top of* standard pipelines.

## Run it

Requires macOS or Linux, LLVM 23 (`brew install llvm`), Python 3.12, and [Ollama](https://ollama.com) with `llama3.1` for the agent.

```bash
git clone https://github.com/aryaMehta26/passpilot.git
cd passpilot
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

make plugin                                   # build the C++ IRFeatures pass plugin
make test                                     # 27 tests
python -m passpilot run --bench crc32 quicksort --budget 10   # quick run
python -m passpilot run                       # the full experiment (resumable)
python -m passpilot report                    # charts + tables
```

Set `LLVM_PREFIX` if LLVM isn't in `/opt/homebrew/opt/llvm`.

<details>
<summary><b>Project layout</b></summary>

```
passpilot/
├── benchmarks/            # 12 C kernels + bench.h (seeded LCG, checksum output)
├── plugin/IRFeatures.cpp  # LLVM pass plugin (C++): IR features as JSON
├── passpilot/
│   ├── config.py          # pass catalog with adaptor nesting, budgets, paths
│   ├── pipeline.py        # validate a pass list → opt pipeline string
│   ├── toolchain.py       # compile, link, warm up, time, check correctness
│   ├── features.py        # IR features + pipeline encoding
│   ├── remarks.py         # LLVM missed-optimization remarks
│   ├── evaluator.py       # shared budget, cache, per-candidate log
│   ├── search.py          # random search, genetic algorithm
│   ├── agent.py           # LLM agent: prompt, JSON interface, repair, fallback
│   ├── costmodel.py       # XGBoost cost model, leave-one-benchmark-out
│   ├── experiment.py      # baselines → search → cost model → confirm
│   └── report.py          # charts and tables
├── tests/                 # unit tests + LLVM integration tests
├── data/                  # every evaluation, confirmed results, summary.json
└── docs/                  # header and charts
```
</details>

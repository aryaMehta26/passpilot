"""python -m passpilot run [--bench ...] [--methods ...] [--budget N] | python -m passpilot report"""
import argparse
import json

from .config import BENCHMARKS, BUDGET


def main():
    ap = argparse.ArgumentParser(prog="passpilot")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="run the experiment (resumable)")
    r.add_argument("--bench", nargs="+", choices=BENCHMARKS)
    r.add_argument("--methods", nargs="+", default=["random", "ga", "agent", "model"],
                   choices=["random", "ga", "agent", "model"])
    r.add_argument("--budget", type=int, default=BUDGET)
    sub.add_parser("report", help="charts + tables from data/")
    a = ap.parse_args()
    if a.cmd == "run":
        from .experiment import run
        print(json.dumps(run(a.bench, a.methods, a.budget), indent=2))
    else:
        from .report import report
        report()


if __name__ == "__main__":
    main()

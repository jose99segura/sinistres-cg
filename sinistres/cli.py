"""Command line: `uv run sinistres build | ask | eval | serve`."""

import argparse
import json
import sys


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="sinistres")
    sub = parser.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="download, parse and segment the contracts into SQLite")
    b.add_argument("--only", nargs="*", help="contract ids to build (default: all)")
    sub.add_parser("stats", help="clause counts per contract and kind")

    a = sub.add_parser("ask", help="analyse one claim against one contract")
    a.add_argument("contract")
    a.add_argument("claim")

    e = sub.add_parser("eval", help="run the evaluation set and print the report")
    e.add_argument("--only", nargs="*", help="case ids")
    e.add_argument("--out", default="eval/results/latest.json")
    e.add_argument("--mode", choices=["cascade", "cheap", "strong", "long"], default="cascade",
                   help="cascade, cheap (small model only), strong (stronger model on retrieved clauses), long (whole contract)")

    s = sub.add_parser("serve", help="run the web app")
    s.add_argument("--port", type=int, default=8080)

    args = parser.parse_args()
    if args.cmd == "build":
        from .ingest.build import build
        build(args.only)
    elif args.cmd == "stats":
        from .ingest.build import stats
        print(stats())
    elif args.cmd == "ask":
        from .answer.analyse import analyse
        print(json.dumps(analyse(args.contract, args.claim), ensure_ascii=False, indent=1))
    elif args.cmd == "eval":
        from .evaluate import run
        run(args.only, args.out, args.mode)
    elif args.cmd == "serve":
        import uvicorn
        uvicorn.run("sinistres.api:app", host="0.0.0.0", port=args.port)

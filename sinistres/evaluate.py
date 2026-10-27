"""Run eval/cases.yaml and report what matters for this task.

- verdict accuracy;
- expected clause cited: did the answer rest on the clause a human marked as decisive;
- citation grounding: share of citations found word for word in the cited clause;
- abstention: when the right answer is "indéterminé", did the system say so, and how often it said
  something confident and wrong (the failure that costs the most).
"""

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor

import yaml

from . import config
from .answer.analyse import analyse

CASES = config.ROOT / "eval" / "cases.yaml"
REPORT = config.ROOT / "eval" / "report.json"
LABELS = {"couvert": "couvert", "non_couvert": "non couvert", "indetermine": "indéterminé"}


def _run_case(case: dict) -> dict:
    try:
        r = analyse(case["contract"], case["claim"])
    except Exception as e:  # one failing case must not lose the run
        return {**case, "error": str(e)}
    verified = [s for s in r["etapes"] if s["verifiee"]]
    patterns = case.get("expected_clauses") or []
    hit = None
    if patterns:
        hit = any(re.search(p, s["clause"]["text"], re.I) for s in verified for p in patterns)
    return {
        "id": case["id"],
        "contract": case["contract"],
        "claim": case["claim"],
        "expected": case["expected"],
        "got": r["verdict"],
        "model_verdict": r["verdict_modele"],
        "accept": case.get("accept") or [case["expected"]],
        "verdict_ok": r["verdict"] in (case.get("accept") or [case["expected"]]),
        "exact": r["verdict"] == case["expected"],
        "expected_clause_hit": hit,
        "citations_total": len(r["etapes"]),
        "citations_verified": len(verified),
        "cited": [f"{s['clause']['id']} p.{s['clause']['page_start']} ({s['role']})" for s in r["etapes"]],
        "resume": r["resume"],
        "missing": r["informations_manquantes"],
        "duration_s": r["duree_s"],
    }


def metrics(results: list[dict]) -> dict:
    ok = [r for r in results if "error" not in r]
    n = len(ok) or 1
    with_clause = [r for r in ok if r["expected_clause_hit"] is not None]
    cit_total = sum(r["citations_total"] for r in ok)
    exp_indet = [r for r in ok if r["expected"] == "indetermine"]
    got_indet = [r for r in ok if r["got"] == "indetermine"]
    return {
        "cases": len(results),
        "errors": len(results) - len(ok),
        "verdict_accuracy": sum(r["verdict_ok"] for r in ok) / n,
        "verdict_exact": sum(r["exact"] for r in ok) / n,
        "expected_clause_recall": (sum(r["expected_clause_hit"] for r in with_clause) / len(with_clause)) if with_clause else None,
        "citation_verified_rate": (sum(r["citations_verified"] for r in ok) / cit_total) if cit_total else None,
        "abstention_recall": (sum(r["got"] == "indetermine" for r in exp_indet) / len(exp_indet)) if exp_indet else None,
        "abstention_precision": (sum(r["expected"] == "indetermine" for r in got_indet) / len(got_indet)) if got_indet else None,
        "wrong_confident_rate": sum(r["got"] != "indetermine" and not r["verdict_ok"] for r in ok) / n,
        "downgraded": sum(r["got"] != r["model_verdict"] for r in ok),
    }


def run(only: list[str] | None, out: str) -> dict:
    cases = yaml.safe_load(CASES.read_text(encoding="utf-8"))["cases"]
    if only:
        cases = [c for c in cases if c["id"] in only]
    with ThreadPoolExecutor(3) as pool:
        results = list(pool.map(_run_case, cases))
    report = {
        "run_at": time.strftime("%Y-%m-%d %H:%M"),
        "model": config.MISTRAL_MODEL,
        "metrics": metrics(results),
        "cases": results,
    }
    (config.ROOT / out).parent.mkdir(parents=True, exist_ok=True)
    (config.ROOT / out).write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    if not only:
        REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(markdown(report))
    return report


def markdown(report: dict) -> str:
    m = report["metrics"]
    pct = lambda x: "—" if x is None else f"{x * 100:.0f} %"
    lines = [
        f"| Metric | Value |",
        f"|---|---|",
        f"| Cases | {m['cases']} ({m['errors']} errors) |",
        f"| Verdict acceptable | {pct(m['verdict_accuracy'])} |",
        f"| Verdict equal to the expected one | {pct(m['verdict_exact'])} |",
        f"| Expected clause cited | {pct(m['expected_clause_recall'])} |",
        f"| Citations found word for word | {pct(m['citation_verified_rate'])} |",
        f"| Abstention recall (said \"indéterminé\" when it should) | {pct(m['abstention_recall'])} |",
        f"| Abstention precision | {pct(m['abstention_precision'])} |",
        f"| Confident and wrong | {pct(m['wrong_confident_rate'])} |",
        f"| Verdicts downgraded by the checks | {m['downgraded']} |",
        "",
        "| Case | Contract | Expected | Got | Expected clause cited | Citations verified |",
        "|---|---|---|---|---|---|",
    ]
    for r in report["cases"]:
        if "error" in r:
            lines.append(f"| {r['id']} | {r['contract']} | {LABELS[r['expected']]} | error | — | — |")
            continue
        mark = "✓" if r["verdict_ok"] else "✗"
        hit = "—" if r["expected_clause_hit"] is None else ("✓" if r["expected_clause_hit"] else "✗")
        lines.append(f"| {r['id']} | {r['contract']} | {LABELS[r['expected']]} | {mark} {LABELS[r['got']]} | {hit} | {r['citations_verified']}/{r['citations_total']} |")
    return "\n".join(lines)

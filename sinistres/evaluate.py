"""Run eval/cases.yaml and report what matters for this task.

- verdict accuracy, overall and per slice (guarantee, exclusion, exception, condition, ambiguous...),
  with a 95% Wilson interval: on a few dozen cases the interval matters as much as the number;
- expected clause cited: did the answer rest on the clause a human marked as decisive;
- citation grounding: share of citations found word for word in the cited clause;
- abstention: when the right answer is "indéterminé", did the system say so, and how often it said
  something confident and wrong (the failure that costs the most);
- cost: how often the cascade escalated to the stronger model.

Three modes compare designs on the same cases: `cascade` (what is deployed), `cheap` (first model
only) and `long` (no retrieval: every clause of the contract to the stronger model in one call).
"""

import json
import math
import re
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

import yaml

from . import config
from .answer.analyse import analyse

CASES = config.ROOT / "eval" / "cases.yaml"
REPORT = config.ROOT / "eval" / "report.json"
LABELS = {"couvert": "couvert", "non_couvert": "non couvert", "indetermine": "indéterminé"}


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float] | None:
    """95% confidence interval for a proportion k/n (Wilson score)."""
    if not n:
        return None
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return max(0.0, centre - half), min(1.0, centre + half)


def _run_case(case: dict, mode: str) -> dict:
    try:
        r = analyse(case["contract"], case["claim"], mode=mode)
    except Exception as e:  # one failing case must not lose the run
        return {**case, "error": str(e)}
    verified = [s for s in r["etapes"] if s["verifiee"]]
    patterns = case.get("expected_clauses") or []
    hit = None
    if patterns:
        hit = any(re.search(p, s["clause"]["text"], re.I) for s in verified for p in patterns)
    accept = case.get("accept") or [case["expected"]]
    return {
        "id": case["id"],
        "slice": case.get("slice", "other"),
        "contract": case["contract"],
        "claim": case["claim"],
        "expected": case["expected"],
        "got": r["verdict"],
        "model_verdict": r["verdict_modele"],
        "accept": accept,
        "verdict_ok": r["verdict"] in accept,
        "exact": r["verdict"] == case["expected"],
        "expected_clause_hit": hit,
        "citations_total": len(r["etapes"]),
        "citations_verified": len(verified),
        "escalated": bool(r.get("escalade")),
        "model": r["modele"],
        "cited": [f"{s['clause']['id']} p.{s['clause']['page_start']} ({s['role']})" for s in r["etapes"]],
        "resume": r["resume"],
        "missing": r["informations_manquantes"],
        "duration_s": r["duree_s"],
    }


def metrics(results: list[dict]) -> dict:
    ok = [r for r in results if "error" not in r]
    n = len(ok)
    with_clause = [r for r in ok if r["expected_clause_hit"] is not None]
    cit_total = sum(r["citations_total"] for r in ok)
    exp_indet = [r for r in ok if r["expected"] == "indetermine"]
    got_indet = [r for r in ok if r["got"] == "indetermine"]
    acc_k = sum(r["verdict_ok"] for r in ok)
    wrong_k = sum(r["got"] != "indetermine" and not r["verdict_ok"] for r in ok)
    slices = defaultdict(list)
    for r in ok:
        slices[r["slice"]].append(r["verdict_ok"])
    return {
        "cases": len(results),
        "errors": len(results) - n,
        "verdict_accuracy": acc_k / n if n else None,
        "verdict_accuracy_ci": wilson(acc_k, n),
        "verdict_exact": sum(r["exact"] for r in ok) / n if n else None,
        "expected_clause_recall": (sum(r["expected_clause_hit"] for r in with_clause) / len(with_clause)) if with_clause else None,
        "citation_verified_rate": (sum(r["citations_verified"] for r in ok) / cit_total) if cit_total else None,
        "abstention_recall": (sum(r["got"] == "indetermine" for r in exp_indet) / len(exp_indet)) if exp_indet else None,
        "abstention_precision": (sum(r["expected"] == "indetermine" for r in got_indet) / len(got_indet)) if got_indet else None,
        "wrong_confident_rate": wrong_k / n if n else None,
        "wrong_confident_ci": wilson(wrong_k, n),
        "downgraded": sum(r["got"] != r["model_verdict"] for r in ok),
        "escalation_rate": sum(r["escalated"] for r in ok) / n if n else None,
        "mean_duration_s": round(sum(r["duration_s"] for r in ok) / n, 1) if n else None,
        "by_slice": {s: {"n": len(v), "ok": sum(v)} for s, v in sorted(slices.items())},
    }


def run(only: list[str] | None, out: str, mode: str = "cascade") -> dict:
    cases = yaml.safe_load(CASES.read_text(encoding="utf-8"))["cases"]
    if only:
        cases = [c for c in cases if c["id"] in only]
    with ThreadPoolExecutor(3) as pool:
        results = list(pool.map(lambda c: _run_case(c, mode), cases))
    model = {"cascade": f"{config.MISTRAL_MODEL} → {config.ESCALATION_MODEL}",
             "cheap": config.MISTRAL_MODEL, "long": config.ESCALATION_MODEL}[mode]
    report = {
        "run_at": time.strftime("%Y-%m-%d %H:%M"),
        "mode": mode,
        "model": model,
        "metrics": metrics(results),
        "cases": results,
    }
    (config.ROOT / out).parent.mkdir(parents=True, exist_ok=True)
    (config.ROOT / out).write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    if not only and mode == "cascade":
        REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(markdown(report))
    return report


def markdown(report: dict) -> str:
    m = report["metrics"]
    pct = lambda x: "—" if x is None else f"{x * 100:.0f} %"
    ci = lambda c: "" if not c else f" ({c[0] * 100:.0f}–{c[1] * 100:.0f})"
    lines = [
        "| Metric | Value |",
        "|---|---|",
        f"| Mode | {report.get('mode', 'cascade')} — `{report['model']}` |",
        f"| Cases | {m['cases']} ({m['errors']} errors) |",
        f"| Verdict acceptable (95% CI) | {pct(m['verdict_accuracy'])}{ci(m.get('verdict_accuracy_ci'))} |",
        f"| Verdict equal to the expected one | {pct(m['verdict_exact'])} |",
        f"| Expected clause cited | {pct(m['expected_clause_recall'])} |",
        f"| Citations found word for word | {pct(m['citation_verified_rate'])} |",
        f"| Abstention recall (said \"indéterminé\" when it should) | {pct(m['abstention_recall'])} |",
        f"| Abstention precision | {pct(m['abstention_precision'])} |",
        f"| Confident and wrong (95% CI) | {pct(m['wrong_confident_rate'])}{ci(m.get('wrong_confident_ci'))} |",
        f"| Verdicts downgraded by the checks | {m['downgraded']} |",
        f"| Escalated to the stronger model | {pct(m.get('escalation_rate'))} |",
        f"| Mean time per claim | {m.get('mean_duration_s')} s |",
        "",
        "| Slice | Acceptable |",
        "|---|---|",
    ]
    for s, v in m.get("by_slice", {}).items():
        lines.append(f"| {s} | {v['ok']}/{v['n']} |")
    lines += ["", "| Case | Slice | Expected | Got | Expected clause cited | Citations verified |", "|---|---|---|---|---|---|"]
    for r in report["cases"]:
        if "error" in r:
            lines.append(f"| {r['id']} | {r.get('slice', '')} | {LABELS[r['expected']]} | error | — | — |")
            continue
        mark = "✓" if r["verdict_ok"] else "✗"
        hit = "—" if r["expected_clause_hit"] is None else ("✓" if r["expected_clause_hit"] else "✗")
        lines.append(f"| {r['id']} | {r['slice']} | {LABELS[r['expected']]} | {mark} {LABELS[r['got']]} | {hit} | {r['citations_verified']}/{r['citations_total']} |")
    return "\n".join(lines)

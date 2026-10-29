"""Claim + contract -> verdict, reasons, and the clauses it rests on, checked.

The model proposes; the code checks. Every citation must be found word for word in the clause it
claims to come from, and a verdict must rest on the right kind of clause: "couvert" needs a verified
guarantee, "non couvert" a verified exclusion, condition or scope. When a check fails the verdict is
downgraded to "indéterminé" and the reason is shown, rather than shipping an unsupported answer.
"""

import re
import time
import unicodedata
from typing import Literal

from pydantic import BaseModel, Field

from .. import config, db, llm
from .retrieve import claim_facts, retrieve

Verdict = Literal["couvert", "non_couvert", "indetermine"]
Role = Literal["garantie", "exclusion", "condition", "definition", "limite"]


class Step(BaseModel):
    clause_id: str
    citation: str = Field(description="the decisive words, copied exactly from the clause, 5 to 40 words")
    role: Role
    explication: str = Field(description="one French sentence: what this clause means for this claim")


Finding = Literal["oui", "non", "incertain"]


class Decision(BaseModel):
    # The model reports findings; the verdict is derived from them by `verdict_from` in code. Field
    # order is generation order: facts and citations come before the findings that rest on them.
    qualification: str = Field(
        description="in French: what the damaged property and the event are in the contract's own terms, "
                    "naming the definition used (e.g. a bike is an 'objet de mobilité durable')")
    etapes: list[Step]
    garantie: Finding = Field(description="does a guarantee cover this property and this event?")
    exclusion: Finding = Field(description="do the facts given fall under an exclusion?")
    exclusion_fait: str | None = Field(
        description="the words of the claim that support 'oui' or 'incertain' for exclusion, copied exactly; null otherwise")
    condition_non_remplie: Finding = Field(
        description="do the facts given show that a condition of cover or an obligation was NOT met?")
    condition_fait: str | None = Field(
        description="the words of the claim that support 'oui' or 'incertain' for condition_non_remplie, copied exactly; null otherwise")
    informations_manquantes: list[str] = Field(
        description="facts not given in the claim that would change a finding, as questions in French")
    garanties_a_verifier: list[str] = Field(
        description="optional guarantees this answer assumes subscribed, to check in the Conditions Particulières")
    resume: str = Field(description="2 or 3 French sentences for the policyholder, consistent with the findings")


DECIDE_SYSTEM = """Tu es gestionnaire sinistres. Tu examines si un sinistre est couvert par des conditions générales
d'assurance habitation, en t'appuyant UNIQUEMENT sur les clauses fournies (identifiant entre crochets).
Tu ne donnes pas de verdict : tu établis trois constats, et le verdict en est déduit.

Méthode :
1. qualification : nomme le bien et l'événement avec les mots du contrat (quelle définition). Un vélo n'est pas
   un véhicule à moteur ; une table de jardin est du mobilier de jardin.
2. etapes : cite la garantie examinée, puis les exclusions, conditions et définitions décisives.
3. Constats, chacun "oui", "non" ou "incertain" :
   - garantie : une garantie couvre-t-elle ce bien et cet événement ? (si elle est optionnelle, suppose-la
     souscrite et nomme-la dans garanties_a_verifier)
   - exclusion : les faits RACONTÉS tombent-ils sous une exclusion ?
   - condition_non_remplie : les faits RACONTÉS montrent-ils qu'une condition ou obligation n'a PAS été respectée ?

Règles pour les constats :
- Juge sur les faits racontés. Ce que le récit ne dit pas est présumé normal : obligations respectées, entretien
  fait, plainte déposée, option souscrite. Ces réserves génériques vont dans informations_manquantes ou
  garanties_a_verifier, elles ne rendent PAS un constat "incertain".
- "incertain" seulement quand un fait raconté peut se lire des deux façons au regard du texte (un local fermé
  mais pas à clé est-il « non clos » ?), ou quand un fait décisif propre à ce sinistre manque (le vélo
  était-il attaché ?). Pose alors la question précise dans informations_manquantes.
- Pour exclusion et condition_non_remplie, "oui" ou "incertain" exige de recopier dans exclusion_fait /
  condition_fait les mots EXACTS du récit qui le justifient. Si aucun mot du récit ne le justifie, le constat est "non".
- Une exclusion ne s'applique que si le bien ou la circonstance correspond à ce qu'elle vise. Pas d'analogie.
- Avant de conclure qu'une exclusion s'applique, cherche dans la clause et autour d'elle une exception
  (« sauf », « toutefois », « à moins que », « excepté ») qui rendrait la garantie à nouveau applicable.
- Ne t'arrête pas à la première raison de refuser : examine aussi les autres garanties qui pourraient couvrir le bien
  (une option « tous risques » ou un pack spécifique peut couvrir ce que la garantie de base exclut).

Règles pour les citations :
- Chaque étape cite un clause_id fourni et recopie MOT POUR MOT un extrait de cette clause (pas de reformulation,
  pas de guillemets, pas de gras ni de mise en forme, pas de numéro d'article ajouté). N'invente aucune clause.
- Réponds en français, simplement, pour l'assuré."""



# Check messages shown under "How the answer was built", in the UI's language.
MESSAGES = {
    "fr": {
        "finding_dropped": "Constat « {label} » écarté : il ne s'appuie sur aucun fait du récit.",
        "label_exclusion": "exclusion",
        "label_condition": "condition non remplie",
        "step_dropped": "Étape écartée : la clause {id} n'existe pas dans les extraits fournis.",
        "moved": "Citation rattachée à la clause {to} (le modèle indiquait {frm}).",
        "verified": "{ok}/{n} citations retrouvées mot pour mot dans le contrat.",
        "unverified": "{n} citation(s) introuvable(s) dans le texte : ignorée(s) pour le verdict.",
        "downgraded": "Verdict rétrogradé en « indéterminé » : {why}.",
        "why_covered": "« couvert » sans garantie citée et vérifiée",
        "why_not_covered": "« non couvert » sans la clause décisive citée et vérifiée",
        "escalated": "Repris par {to} ({reason}) : {first} avait conclu « {verdict} ».",
        "reason_denial": "refus, toujours relu par le modèle le plus fort",
        "reason_downgraded": "verdict non sourcé",
        "reason_undetermined": "réponse indéterminée",
        "reason_citations": "trop de citations introuvables",
        "escalation_failed": "Le modèle de relecture n'a pas répondu : réponse du premier modèle conservée.",
        "exception": "Exception relevée dans la clause : « {text} ».",
        "review_rejected": "Relecture du refus : la clause ne fonde pas le refus ({why}) → « indéterminé ».",
        "review_ok": "Relecture du refus : la clause décisive s'applique bien aux faits racontés.",
    },
    "en": {
        "finding_dropped": "Finding “{label}” dropped: it rests on no fact of the claim.",
        "label_exclusion": "exclusion",
        "label_condition": "condition not met",
        "step_dropped": "Step dropped: clause {id} is not among the clauses provided.",
        "moved": "Citation attached to clause {to} (the model said {frm}).",
        "verified": "{ok}/{n} citations found word for word in the contract.",
        "unverified": "{n} citation(s) not found in the text: ignored for the verdict.",
        "downgraded": "Verdict downgraded to “undetermined”: {why}.",
        "why_covered": "“covered” without a cited and verified guarantee",
        "why_not_covered": "“not covered” without the deciding clause cited and verified",
        "escalated": "Taken over by {to} ({reason}): {first} had concluded “{verdict}”.",
        "reason_denial": "a denial, always reviewed by the stronger model",
        "reason_downgraded": "unsourced verdict",
        "reason_undetermined": "undetermined answer",
        "reason_citations": "too many citations not found",
        "escalation_failed": "The review model did not answer: the first model's answer is kept.",
        "exception": "Exception found in the clause: “{text}”.",
        "review_rejected": "Denial review: the clause does not ground the refusal ({why}) → “undetermined”.",
        "review_ok": "Denial review: the deciding clause does apply to the facts told.",
    },
}

LANG_INSTRUCTION = {
    "fr": "",
    "en": ("\n\nLANGUE DE RÉPONSE : anglais. Écris qualification, explication, informations_manquantes, "
           "garanties_a_verifier et resume en anglais. Les citations restent recopiées du contrat, en français, mot pour mot."),
}


def _msg(lang: str, key: str, **kw) -> str:
    return MESSAGES[lang][key].format(**kw)


def ground_findings(d: Decision, claim: str, checks: list[str], lang: str = "fr") -> None:
    """An exclusion or an unmet condition must rest on words of the claim. Without them, the presumption
    holds (the policyholder met their obligations) and the finding becomes "non"."""
    for finding, fact in (("exclusion", "exclusion_fait"), ("condition_non_remplie", "condition_fait")):
        if getattr(d, finding) == "non":
            continue
        words = getattr(d, fact)
        if not words or not find_citation(words, claim):
            label = _msg(lang, "label_exclusion" if finding == "exclusion" else "label_condition")
            checks.append(_msg(lang, "finding_dropped", label=label))
            setattr(d, finding, "non")


def verdict_from(d: Decision) -> Verdict:
    """The decision rule, in one place: a guarantee must apply and nothing must take it away."""
    if d.garantie == "non" or d.exclusion == "oui" or d.condition_non_remplie == "oui":
        return "non_couvert"
    if d.garantie == "oui" and d.exclusion == "non" and d.condition_non_remplie == "non":
        return "couvert"
    return "indetermine"


# ---------------------------------------------------------------- citation checks

_QUOTES = str.maketrans({"’": "'", "‘": "'", "«": '"', "»": '"', "“": '"', "”": '"', " ": " ", "–": "-", "—": "-"})


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFC", s).translate(_QUOTES).lower()
    s = s.replace("**", "").replace("__", "")  # markdown emphasis the model adds inside quotes
    s = re.sub(r"(\w)- (\w)", r"\1\2", s)  # words hyphenated across a line break
    s = s.replace("-", " ")  # "c'est-à-dire" and "c'est à dire" are the same words
    return re.sub(r"\s+", " ", s).strip(" .;,:\"'")


def find_citation(citation: str, clause_text: str) -> tuple[int, int] | None:
    """Span of the citation in the normalised clause text, allowing '…' between fragments."""
    text = _norm(clause_text)
    parts = [p for p in (_norm(x) for x in re.split(r"\.\.\.|…|\[\.\.\.\]", citation)) if len(p) >= 3]
    if not parts:
        return None
    pos, first = 0, None
    for p in parts:
        i = text.find(p, pos)
        if i < 0:
            return None
        first = i if first is None else first
        pos = i + len(p)
    return first, pos


def _highlight_lines(conn, clause: dict, span: tuple[int, int]) -> list[int]:
    """Line numbers of the clause that the citation covers (for the PDF highlight)."""
    lines = db.clause_lines(conn, clause["id"])
    out, offset = [], 0
    norm_texts = [_norm(l["text"]) for l in lines]
    for l, t in zip(lines, norm_texts):
        start, end = offset, offset + len(t)
        if end >= span[0] and start <= span[1] and t:
            out.append(l["n"])
        offset = end + 1
    return out or [l["n"] for l in lines]


# ---------------------------------------------------------------- the pipeline


def _fmt_clause(c: dict) -> str:
    head = f"[{c['id']}] ({c['kind']}) p.{c['page_start']} — {c['section_path']}"
    return f"{head}\n{c['text']}"


def _decide(conn, contract, claim: str, clauses: list[dict], lang: str, model: str) -> dict:
    """One decision by one model, checked. Returns the checked answer, not yet the final one."""
    by_id = {c["id"]: c for c in clauses}
    user = (
        f"CONTRAT : {contract['insurer']} — {contract['product']} ({contract['version']})\n\n"
        f"SINISTRE DÉCLARÉ :\n{claim}\n\n"
        f"CLAUSES ({len(clauses)}) :\n\n" + "\n\n".join(_fmt_clause(c) for c in clauses)
    )
    decision = llm.structured(DECIDE_SYSTEM + LANG_INSTRUCTION[lang], user, Decision, model=model)

    # Check every step against the database.
    checks: list[str] = []
    steps = []
    for s in decision.etapes:
        clause = by_id.get(s.clause_id)
        if not clause:
            checks.append(_msg(lang, "step_dropped", id=s.clause_id))
            continue
        span = find_citation(s.citation, clause["text"])
        if span is None:
            # The words may come from a neighbouring clause: accept them only if they appear, word for
            # word, in exactly one of the clauses the model was given, and say so.
            found = [c for c in clauses if c["id"] != clause["id"] and find_citation(s.citation, c["text"])]
            if len(found) == 1:
                checks.append(_msg(lang, "moved", to=found[0]["id"], frm=clause["id"]))
                clause = found[0]
                span = find_citation(s.citation, clause["text"])
        steps.append({
            **s.model_dump(),
            "clause_id": clause["id"],
            "verifiee": span is not None,
            "clause": {k: clause[k] for k in ("id", "page_start", "page_end", "section_path", "title", "kind", "text")},
            "lignes": _highlight_lines(conn, clause, span) if span else [],
        })
    verified = [s for s in steps if s["verifiee"]]
    n_bad = len(steps) - len(verified)
    if steps:
        checks.append(_msg(lang, "verified", ok=len(verified), n=len(steps)))
    if n_bad:
        checks.append(_msg(lang, "unverified", n=n_bad))

    ground_findings(decision, claim, checks, lang)
    proposed = verdict_from(decision)
    verdict = proposed
    roles = {s["role"] for s in verified}
    downgrade = None
    if verdict == "couvert" and "garantie" not in roles:
        downgrade = "why_covered"
    elif verdict == "non_couvert":
        if decision.exclusion == "oui" and "exclusion" in roles:
            pass
        elif decision.condition_non_remplie == "oui" and "condition" in roles:
            pass
        elif decision.garantie == "non" and roles & {"garantie", "definition", "exclusion"}:
            pass
        else:
            downgrade = "why_not_covered"
    if downgrade:
        checks.append(_msg(lang, "downgraded", why=_msg(lang, downgrade)))
        verdict = "indetermine"
    return {"decision": decision, "steps": steps, "checks": checks, "proposed": proposed,
            "verdict": verdict, "n_bad": n_bad, "model": model}


def _escalation_reason(d: dict) -> str | None:
    """Why the cheap model's answer is not good enough to ship, if it is not."""
    if d["verdict"] == "non_couvert":
        return "denial"  # models over-deny: every refusal gets the stronger model
    if d["verdict"] != d["proposed"]:
        return "downgraded"
    if d["verdict"] == "indetermine":
        return "undetermined"
    if d["steps"] and d["n_bad"] * 3 > len(d["steps"]):
        return "citations"
    return None


class Support(BaseModel):
    supported: bool = Field(description="true only if the quoted clause, read in full, applies to the facts told")
    exception: str | None = Field(description="an exception in the clause ('sauf', 'toutefois', 'à moins que') "
                                              "that could apply to these facts, quoted; null if none")
    raison: str = Field(description="one sentence")


SUPPORT_SYSTEM = """Tu relis un refus de prise en charge. On te donne le sinistre raconté et la clause sur laquelle
repose le refus. Réponds supported=true seulement si cette clause, lue en entier, s'applique bien aux faits racontés
(pas par analogie, pas sur des faits supposés). Cherche dans la clause une exception (« sauf », « toutefois »,
« à moins que », « excepté ») qui pourrait s'appliquer à ces faits : si oui, cite-la dans exception."""


def _review_denial(d: dict, claim: str, lang: str) -> None:
    """Stricter bar for "non couvert": a separate check that the deciding clause supports the refusal."""
    decision = d["decision"]
    wanted = ("exclusion" if decision.exclusion == "oui"
              else "condition" if decision.condition_non_remplie == "oui" else None)
    roles = {wanted} if wanted else {"garantie", "definition"}
    deciding = [s for s in d["steps"] if s["verifiee"] and s["role"] in roles]
    if not deciding:
        return
    s = deciding[0]
    # "No guarantee applies" is a different claim from "an exclusion applies": ask the right question.
    question = ("Le refus dit qu'AUCUNE garantie ne couvre ces faits. Cette clause délimite-t-elle la garantie "
                "de sorte que ces faits n'y entrent pas ?" if wanted is None
                else "Le refus repose sur cette clause d'exclusion ou de condition.")
    review = llm.structured(
        SUPPORT_SYSTEM + LANG_INSTRUCTION[lang],
        f"{question}\n\nSINISTRE :\n{claim}\n\nCLAUSE ({s['clause']['id']}) :\n{s['clause']['text']}",
        Support, model=config.ESCALATION_MODEL,
    )
    if review.exception:
        d["checks"].append(_msg(lang, "exception", text=review.exception))
    if review.supported:
        d["checks"].append(_msg(lang, "review_ok"))
    else:
        d["checks"].append(_msg(lang, "review_rejected", why=review.raison))
        d["verdict"] = "indetermine"


def _examined(clauses: list[dict]) -> dict:
    """What was searched, so that an answer saying 'cannot decide' shows its evidence."""
    by_source: dict[str, int] = {}
    for c in clauses:
        by_source[c["why"]] = by_source.get(c["why"], 0) + 1
    return {"sources": by_source}


def _all_clauses(conn, contract_id: str) -> list[dict]:
    """Every clause of the contract, for the long-context baseline (no retrieval)."""
    ids = [r[0] for r in conn.execute(
        "select id from clauses where contract_id = ? and kind != 'administratif' order by ord", (contract_id,))]
    clauses = db.clauses_by_ids(conn, ids)
    for c in clauses:
        c["why"] = "tout"
    return clauses


def analyse(contract_id: str, claim: str, lang: str = "fr", mode: str = "cascade") -> dict:
    """mode: "cascade" (deployed), "cheap" (first model only) or "long" (whole contract, stronger model,
    no retrieval: the baseline the evaluation compares against)."""
    t0 = time.monotonic()
    conn = db.connect(readonly=True)
    contract = conn.execute("select * from contracts where id = ?", (contract_id,)).fetchone()
    if not contract:
        raise ValueError(f"unknown contract {contract_id}")

    facts = claim_facts(claim)
    if mode == "long":
        clauses = _all_clauses(conn, contract_id)
        coverage = {"lues": len(clauses), "total": len(clauses)}
    else:
        clauses, coverage = retrieve(conn, contract_id, facts)

    # Cascade: the cheap model answers; the stronger one takes over when that answer is not good enough.
    first_model = config.ESCALATION_MODEL if mode == "long" else config.MISTRAL_MODEL
    d = _decide(conn, contract, claim, clauses, lang, first_model)
    escalation = None
    reason = (_escalation_reason(d) if mode == "cascade" and config.CASCADE and config.GEMINI_API_KEY else None)
    if reason:
        first = d
        try:
            d = _decide(conn, contract, claim, clauses, lang, config.ESCALATION_MODEL)
            escalation = {"reason": reason, "first_model": first["model"], "first_verdict": first["verdict"]}
            d["checks"].insert(0, _msg(lang, "escalated", reason=_msg(lang, f"reason_{reason}"),
                                       first=first["model"], verdict=first["verdict"], to=d["model"]))
        except llm.LLMError:
            d = first
            d["checks"].append(_msg(lang, "escalation_failed"))
    if mode == "cascade" and d["verdict"] == "non_couvert" and config.GEMINI_API_KEY:
        try:
            _review_denial(d, claim, lang)
        except llm.LLMError:
            d["checks"].append(_msg(lang, "escalation_failed"))

    decision = d["decision"]
    return {
        "contract": dict(contract),
        "claim": claim,
        "verdict": d["verdict"],
        "verdict_modele": d["proposed"],
        "constats": {"garantie": decision.garantie, "exclusion": decision.exclusion,
                     "condition_non_remplie": decision.condition_non_remplie},
        "resume": decision.resume,
        "qualification": decision.qualification,
        "etapes": d["steps"],
        "informations_manquantes": decision.informations_manquantes,
        "garanties_a_verifier": decision.garanties_a_verifier,
        "controles": d["checks"],
        "analyse_sinistre": facts.model_dump(),
        "clauses_lues": coverage | {"ids": [c["id"] for c in clauses]},
        "examine": _examined(clauses),
        "escalade": escalation,
        "modele": d["model"] if not escalation else f"{escalation['first_model']} → {d['model']}",
        "duree_s": round(time.monotonic() - t0, 1),
    }

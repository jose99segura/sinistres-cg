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


def analyse(contract_id: str, claim: str, lang: str = "fr") -> dict:
    t0 = time.monotonic()
    conn = db.connect(readonly=True)
    contract = conn.execute("select * from contracts where id = ?", (contract_id,)).fetchone()
    if not contract:
        raise ValueError(f"unknown contract {contract_id}")

    facts = claim_facts(claim)
    clauses, coverage = retrieve(conn, contract_id, facts)
    by_id = {c["id"]: c for c in clauses}

    user = (
        f"CONTRAT : {contract['insurer']} — {contract['product']} ({contract['version']})\n\n"
        f"SINISTRE DÉCLARÉ :\n{claim}\n\n"
        f"CLAUSES ({len(clauses)}) :\n\n" + "\n\n".join(_fmt_clause(c) for c in clauses)
    )
    decision = llm.structured(DECIDE_SYSTEM + LANG_INSTRUCTION[lang], user, Decision)

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

    return {
        "contract": dict(contract),
        "claim": claim,
        "verdict": verdict,
        "verdict_modele": proposed,
        "constats": {"garantie": decision.garantie, "exclusion": decision.exclusion,
                     "condition_non_remplie": decision.condition_non_remplie},
        "resume": decision.resume,
        "qualification": decision.qualification,
        "etapes": steps,
        "informations_manquantes": decision.informations_manquantes,
        "garanties_a_verifier": decision.garanties_a_verifier,
        "controles": checks,
        "analyse_sinistre": facts.model_dump(),
        "clauses_lues": coverage | {"ids": [c["id"] for c in clauses]},
        "modele": config.MISTRAL_MODEL,
        "duree_s": round(time.monotonic() - t0, 1),
    }

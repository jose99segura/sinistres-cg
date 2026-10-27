"""From a claim in plain French to the handful of clauses worth reading.

No vector store: the clauses already carry the contract's own structure (section path, kind, perils),
so retrieval is SQL. Three sources are merged:

1. structure: every guarantee, exclusion, condition and limit labelled with the claim's perils;
2. words: full-text search (SQLite FTS5, BM25) on the terms a handler would look up;
3. definitions: the contract's definitions of the words used in 1 and 2 ("dépendances", "effraction"),
   plus the exclusions that apply to every guarantee.
"""

import re
from collections import OrderedDict

from pydantic import BaseModel, Field

from .. import db, llm
from ..taxonomy import Peril


class ClaimFacts(BaseModel):
    perils: list[Peril] = Field(description="1 to 3 perils the claim falls under, most likely first")
    biens: list[str] = Field(description="the damaged or stolen property, in French")
    lieu: str | None = Field(description="where it happened, if said")
    termes: list[str] = Field(description="4 to 10 French words or short phrases to look up in the contract")


FACTS_SYSTEM = """You read a home-insurance claim written by a policyholder in French.
Return:
- perils: the 1 to 3 most relevant among general, incendie, degats_des_eaux, tempete_grele_neige,
  catastrophes_naturelles, vol_vandalisme, bris_de_glace, dommages_electriques, objets_valeur_tous_risques
  (valuables, multimedia, leisure items, bicycles), jardin_exterieurs (garden, outdoor furniture, pool),
  responsabilite_civile, protection_juridique, assistance, pertes_indirectes.
- biens: the damaged or stolen property.
- lieu: where it happened.
- termes: words an insurance contract would use for this situation, e.g. "vélo", "cycle", "local commun",
  "parties communes", "effraction", "dépendances", "mobilier de jardin", "absence", "inoccupation",
  "chaleur", "incendie", "combustion". Single words or short phrases, in French."""

RETRIEVE_KINDS = ("garantie", "exclusion", "condition", "limite")
MAX_CLAUSES = 60


def claim_facts(claim: str) -> ClaimFacts:
    return llm.structured(FACTS_SYSTEM, claim, ClaimFacts)


def _fts_query(terms: list[str]) -> str:
    # Each term becomes a quoted phrase; FTS5 syntax characters are stripped.
    phrases = []
    for t in terms:
        words = re.findall(r"\w+", t.lower())
        if words:
            phrases.append('"' + " ".join(words) + '"')
    return " OR ".join(phrases)


def retrieve(conn, contract_id: str, facts: ClaimFacts) -> tuple[list[dict], dict]:
    picked: OrderedDict[str, str] = OrderedDict()  # clause id -> why it was picked

    def add(ids, why):
        for i in ids:
            picked.setdefault(i, why)

    # 1. Words first: they are the most specific signal.
    query = _fts_query(facts.termes + facts.biens)
    if query:
        rows = conn.execute(
            """select f.clause_id from clauses_fts f join clauses c on c.id = f.clause_id
               where clauses_fts match ? and c.contract_id = ? and c.kind != 'administratif'
               order by bm25(clauses_fts) limit 25""",
            (query, contract_id),
        ).fetchall()
        add([r[0] for r in rows], "texte")

    # 2. Structure: the guarantee chapters of the claim's perils.
    marks = ",".join("?" * len(facts.perils))
    kinds = ",".join("?" * len(RETRIEVE_KINDS))
    rows = conn.execute(
        f"""select distinct c.id from clauses c join clause_perils p on p.clause_id = c.id
            where c.contract_id = ? and p.peril in ({marks}) and c.kind in ({kinds})
            order by c.ord""",
        (contract_id, *facts.perils, *RETRIEVE_KINDS),
    ).fetchall()
    add([r[0] for r in rows], "péril")

    # 3. Exclusions and conditions that apply to every guarantee.
    rows = conn.execute(
        """select c.id from clauses c join clause_perils p on p.clause_id = c.id
           where c.contract_id = ? and p.peril = 'general' and c.kind in ('exclusion', 'condition')
           order by c.ord""",
        (contract_id,),
    ).fetchall()
    add([r[0] for r in rows], "général")

    ids = list(picked)[:MAX_CLAUSES]
    clauses = db.clauses_by_ids(conn, ids)

    # 4. Definitions of the terms that appear in what was picked or in the claim.
    corpus = " ".join(c["text"].lower() for c in clauses) + " " + " ".join(facts.termes + facts.biens).lower()
    defs = conn.execute(
        "select id, defined_term from clauses where contract_id = ? and kind = 'definition' and defined_term is not null",
        (contract_id,),
    ).fetchall()
    def_ids = [r["id"] for r in defs if r["id"] not in picked and r["defined_term"].lower().strip(" :«»\"") in corpus]
    add(def_ids[:20], "définition")
    clauses = db.clauses_by_ids(conn, list(picked)[:MAX_CLAUSES + 20])

    for c in clauses:
        c["why"] = picked[c["id"]]
    total = conn.execute("select count(*) from clauses where contract_id = ?", (contract_id,)).fetchone()[0]
    return clauses, {"lues": len(clauses), "total": total}

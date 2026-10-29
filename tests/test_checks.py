"""The checks that decide whether an answer is shipped: citations and the verdict rule."""

from sinistres.answer.analyse import Decision, find_citation, ground_findings, verdict_from

CLAUSE = "Sont exclus : les vols des biens situés à l’extérieur des bâtiments assurés ou dans des locaux non clos, c’est-à-dire ouverts."


def test_citation_found_despite_quotes_markdown_and_hyphens():
    assert find_citation("dans des **locaux non clos**, c'est à dire ouverts", CLAUSE)


def test_citation_with_ellipsis_must_keep_order():
    assert find_citation("les vols des biens … locaux non clos", CLAUSE)
    assert not find_citation("locaux non clos … les vols des biens", CLAUSE)


def test_paraphrase_is_rejected():
    assert not find_citation("les vols dans un local ouvert ne sont pas couverts", CLAUSE)


def _decision(**findings) -> Decision:
    base = dict(qualification="", etapes=[], garantie="oui", exclusion="non", exclusion_fait=None,
                condition_non_remplie="non", condition_fait=None, informations_manquantes=[],
                garanties_a_verifier=[], resume="")
    return Decision(**(base | findings))


def test_verdict_rule():
    assert verdict_from(_decision()) == "couvert"
    assert verdict_from(_decision(garantie="non")) == "non_couvert"
    assert verdict_from(_decision(exclusion="oui")) == "non_couvert"
    assert verdict_from(_decision(garantie="incertain")) == "indetermine"
    assert verdict_from(_decision(condition_non_remplie="incertain")) == "indetermine"


def test_doubt_without_words_from_the_claim_is_dropped():
    claim = "Le tuyau de ma machine à laver a lâché."
    checks: list[str] = []
    d = _decision(condition_non_remplie="incertain", condition_fait="la machine n'était pas entretenue")
    ground_findings(d, claim, checks)
    assert d.condition_non_remplie == "non" and checks

    d = _decision(exclusion="oui", exclusion_fait="ma machine à laver a lâché")
    ground_findings(d, claim, checks)
    assert d.exclusion == "oui"


def test_contract_in_force_picks_the_edition_of_the_date_of_loss():
    import sqlite3

    from sinistres.db import SCHEMA, contract_in_force

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    for cid, eff in (("p-2017", "2017-06"), ("p-2022", "2022-03")):
        conn.execute("insert into contracts values (?,?,?,?,?,?,?,?,?,?,?)",
                     (cid, "p", "Insurer", "Product", eff, eff, "u", "h", 1, 1, "m"))
    assert contract_in_force(conn, "p", "2020-05-01")["id"] == "p-2017"
    assert contract_in_force(conn, "p", "2023-01-15")["id"] == "p-2022"
    assert contract_in_force(conn, "p", "2016-01-01") is None

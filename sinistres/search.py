"""French text matching for full-text search: light stemming and an insurance synonym table.

SQLite's FTS5 tokenizer does not stem French, so "dégât" would miss "dégâts" and "vélo" would never
find "cycle". Clauses are indexed on a normalised copy of their text, and claim terms are normalised
and expanded with the synonyms below before the query. The table is written by hand on purpose: the
words a policyholder uses and the words a contract uses are domain knowledge, not something an
embedding reliably bridges.
"""

import re
import unicodedata

# Groups of interchangeable terms: a claim word on the left finds contract words anywhere in its group.
SYNONYMS: list[list[str]] = [
    ["vélo", "bicyclette", "cycle", "vtt", "trottinette", "objet de mobilité durable", "mobilité durable", "engin de déplacement"],
    ["vol", "cambriolage", "voleur", "dérobé", "volé", "effraction", "soustraction frauduleuse"],
    ["porte forcée", "effraction", "forcement", "serrure fracturée"],
    ["local commun", "local vélo", "parties communes", "local à vélos", "cave", "garage", "dépendance", "local"],
    ["fermé à clé", "serrure", "verrouillé", "fermeture", "clos", "non clos"],
    ["bougie", "flamme", "feu", "dommages ménagers", "dégâts ménagers", "action subite de la chaleur", "excès de chaleur", "foyer"],
    ["chaleur", "soleil", "canicule", "échauffement", "roussissement"],
    ["fondu", "fondre", "brûlure", "brûlé", "roussi", "déformation"],
    ["table de jardin", "mobilier de jardin", "meubles de jardin", "salon de jardin", "objets situés en plein air", "plein air"],
    ["jardin", "terrasse", "extérieur", "cour", "plein air"],
    ["vacances", "absence", "inoccupation", "inhabité", "voyage", "séjour"],
    ["fuite", "dégâts des eaux", "dégât des eaux", "écoulement", "débordement", "infiltration", "rupture"],
    ["machine à laver", "lave-linge", "appareil à effet d'eau", "appareils à effet d'eau", "électroménager", "tuyau", "conduite"],
    ["parquet", "sol", "revêtement de sol", "embellissements"],
    ["ordinateur", "ordinateur portable", "laptop", "tablette", "matériel informatique", "multimédia", "appareil nomade", "audiovisuel"],
    ["tombé", "chute", "choc", "bris", "casse", "cassé", "accident", "accidentel"],
    ["écran", "vitre", "vitrage", "glace", "bris de glace", "bris de vitrages"],
    ["orage", "tempête", "grêle", "pluie", "intempéries", "ruissellement", "inondation", "précipitations"],
    ["cave", "sous-sol", "cellier"],
    ["bijoux", "objets de valeur", "objets précieux", "montre", "or"],
    ["clé", "clés", "paillasson", "fausses clés"],
    ["store", "store banne", "auvent", "marquise", "volet"],
    ["fils", "fille", "enfant", "membre de la famille", "communauté domestique", "conjoint"],
]

_STOP = {"le", "la", "les", "de", "des", "du", "un", "une", "et", "ou", "a", "à", "au", "aux", "en", "par", "pour",
         "sur", "dans", "que", "qui", "ne", "pas", "se", "sa", "son", "ses", "d", "l", "s", "y", "est", "sont"}


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def stem(word: str) -> str:
    """Very light French stemmer: enough to join singular/plural and masculine/feminine forms."""
    w = _strip_accents(word.lower())
    for suffix in ("ements", "ement", "ations", "ation", "ees", "ee", "es", "s", "x", "e"):
        if w.endswith(suffix) and len(w) - len(suffix) >= 4:
            return w[: -len(suffix)]
    return w


def tokens(text: str) -> list[str]:
    return [stem(w) for w in re.findall(r"[\w']+", text.lower().replace("'", " ")) if w not in _STOP and len(w) > 1]


def normalise(text: str) -> str:
    """What gets indexed: the stemmed tokens of a clause."""
    return " ".join(tokens(text))


def _key(term: str) -> str:
    return " ".join(tokens(term))


_GROUP_OF: dict[str, set[str]] = {}
for _group in SYNONYMS:
    keys = {_key(t) for t in _group if _key(t)}
    for k in keys:
        _GROUP_OF.setdefault(k, set()).update(keys)


def expand(terms: list[str]) -> list[str]:
    """Normalised search phrases for the claim's terms, with their synonyms."""
    out: list[str] = []
    for term in terms:
        k = _key(term)
        if not k:
            continue
        for phrase in [k, *sorted(_GROUP_OF.get(k, ()))]:
            if phrase not in out:
                out.append(phrase)
    return out


def fts_query(terms: list[str]) -> str:
    """FTS5 query over the `stems` column: any of the expanded phrases."""
    return " OR ".join(f'"{p}"' for p in expand(terms))

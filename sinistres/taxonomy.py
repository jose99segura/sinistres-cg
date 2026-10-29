"""The shared vocabulary every contract is mapped onto.

Each insurer names and orders its chapters differently. Labelling every clause with the same small
set of perils and clause kinds is what lets one SQL query work across hundreds of contracts.
"""

from typing import Literal

Peril = Literal[
    "general",  # applies to every guarantee: insured persons, territory, common exclusions, obligations
    "incendie",  # fire, explosion, lightning, smoke
    "degats_des_eaux",
    "tempete_grele_neige",
    "catastrophes_naturelles",  # flood, earthquake, landslide
    "vol_vandalisme",
    "bris_de_glace",
    "dommages_electriques",
    "objets_valeur_tous_risques",  # jewellery, art, multimedia, bikes and leisure equipment, all-risk
    "jardin_exterieurs",  # garden, outdoor furniture, swimming pool
    "responsabilite_civile",
    "protection_juridique",
    "assistance",
    "pertes_indirectes",  # costs and consequential losses: rehousing, rent loss, clean-up
]

PERILS: tuple[str, ...] = Peril.__args__  # type: ignore[attr-defined]

PERIL_LABELS = {
    "general": "Dispositions générales",
    "incendie": "Incendie et risques annexes",
    "degats_des_eaux": "Dégâts des eaux",
    "tempete_grele_neige": "Tempête, grêle, neige",
    "catastrophes_naturelles": "Catastrophes naturelles",
    "vol_vandalisme": "Vol et vandalisme",
    "bris_de_glace": "Bris de glace",
    "dommages_electriques": "Dommages électriques",
    "objets_valeur_tous_risques": "Objets de valeur, tous risques, vélos",
    "jardin_exterieurs": "Jardin et extérieurs",
    "responsabilite_civile": "Responsabilité civile",
    "protection_juridique": "Protection juridique",
    "assistance": "Assistance",
    "pertes_indirectes": "Frais et pertes indirectes",
}

PERIL_LABELS_EN = {
    "general": "General provisions",
    "incendie": "Fire and related perils",
    "degats_des_eaux": "Water damage",
    "tempete_grele_neige": "Storm, hail, snow",
    "catastrophes_naturelles": "Natural disasters",
    "vol_vandalisme": "Theft and vandalism",
    "bris_de_glace": "Glass breakage",
    "dommages_electriques": "Electrical damage",
    "objets_valeur_tous_risques": "Valuables, all-risk, bikes",
    "jardin_exterieurs": "Garden and outdoors",
    "responsabilite_civile": "Liability",
    "protection_juridique": "Legal protection",
    "assistance": "Assistance",
    "pertes_indirectes": "Costs and indirect losses",
}

Kind = Literal[
    "definition",  # defines a term used elsewhere ("Dépendances : ...")
    "garantie",  # what is covered
    "exclusion",  # what is not covered
    "condition",  # a condition of cover or a prevention obligation ("à condition que", "doivent être fermés à clé")
    "limite",  # ceilings, deductibles, valuation rules
    "procedure",  # what to do after a claim, deadlines, proofs
    "administratif",  # premium, duration, termination, law, complaints
    "autre",
]

KIND_LABELS = {
    "definition": "Définition",
    "garantie": "Garantie",
    "exclusion": "Exclusion",
    "condition": "Condition",
    "limite": "Limite / franchise",
    "procedure": "Procédure",
    "administratif": "Administratif",
    "autre": "Autre",
}

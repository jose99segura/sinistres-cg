"use strict";

// UI strings in French and English. Static markup uses data-i18n (text), data-i18n-html (markup)
// and data-i18n-attr="attr:key"; long prose and diagram labels use .lang-fr / .lang-en blocks.
const I18N = {
  fr: {
    "meta.title": "Couvert ou pas ?",
    "h1": "Couvert ou pas ?",
    "tagline": "Décrivez un sinistre. Le système lit les conditions générales, répond <em>couvert</em>, <em>non couvert</em> ou <em>indéterminé</em>, et montre les clauses sur lesquelles il s'appuie.",
    "tab.analyse": "Analyse",
    "tab.methode": "Comment c'est fait",
    "tab.evaluation": "Évaluation",
    "notice": "Démonstration réalisée pour un exercice de recrutement. Contrats publics téléchargés sur les sites des assureurs ; projet personnel, sans lien avec les assureurs cités. Ce n'est pas un avis juridique : seules vos Conditions Particulières et votre assureur font foi.",
    "form.contract": "Le contrat",
    "form.claim": "Le sinistre",
    "form.claim_label": "Description du sinistre",
    "form.placeholder": "Ex. : Mon vélo a été volé dans le local commun de l'immeuble, qui n'était pas fermé à clé.",
    "form.examples": "Exemples :",
    "form.submit": "Analyser le sinistre",
    "form.running": "Analyse en cours…",
    "form.too_short": "Décrivez le sinistre en une ou deux phrases (au moins 15 caractères).",
    "ph.title": "La réponse apparaîtra ici",
    "ph.li1": "<b>Un verdict</b> : couvert, non couvert, ou indéterminé quand le contrat ne permet pas de trancher.",
    "ph.li2": "<b>Les clauses citées</b>, recopiées du contrat, avec la page et la section, surlignées dans le PDF.",
    "ph.li3": "<b>Ce qui déciderait</b> : les faits manquants et les garanties à vérifier dans vos Conditions Particulières.",
    "loading.title": "Analyse en cours…",
    "loading.s1": "Lecture du sinistre (périls, biens, termes)",
    "loading.s2": "Recherche des clauses dans la base",
    "loading.s3": "Constats, vérification des citations et verdict",
    "loading.time": "Environ 10 à 30 secondes (petit modèle, niveau gratuit).",
    "contract.version": "Version",
    "contract.pages": "pages",
    "contract.clauses": "clauses",
    "contract.source": "PDF source",
    "contract.error": "Les contrats ne se chargent pas. Rechargez la page dans un instant.",
    "verdict.couvert": "Couvert",
    "verdict.non_couvert": "Non couvert",
    "verdict.indetermine": "Indéterminé",
    "role.garantie": "Garantie",
    "role.exclusion": "Exclusion",
    "role.condition": "Condition",
    "role.definition": "Définition",
    "role.limite": "Limite",
    "finding.garantie": "Une garantie s'applique",
    "finding.exclusion": "Une exclusion s'applique",
    "finding.condition_non_remplie": "Une condition n'est pas remplie",
    "finding.oui": "oui",
    "finding.non": "non",
    "finding.incertain": "incertain",
    "res.qualification": "Qualification des faits :",
    "res.downgraded": "Les constats menaient à « {v} », mais ce verdict ne reposait pas sur une clause vérifiée : il a été rétrogradé.",
    "res.missing": "Ce qui déciderait",
    "res.missing_none": "Aucun fait manquant signalé.",
    "res.options": "À vérifier dans vos Conditions Particulières",
    "res.options_none": "Aucune garantie optionnelle en jeu.",
    "res.clauses": "Clauses sur lesquelles repose la réponse ({n})",
    "res.clauses_none": "Aucune clause citée.",
    "res.verified": "✓ citation vérifiée",
    "res.verified_title": "Citation retrouvée mot pour mot dans le texte du contrat",
    "res.unverified": "⚠ citation introuvable",
    "res.unverified_title": "Ces mots n'ont pas été retrouvés dans la clause : l'étape n'est pas prise en compte",
    "res.proposed": "Citation proposée par le modèle :",
    "res.see_pdf": "Voir dans le PDF",
    "res.trace": "Comment la réponse a été construite",
    "res.perils": "Périls détectés",
    "res.terms": "Termes recherchés",
    "res.read": "Clauses lues",
    "res.read_n": "{a} sur {b} clauses du contrat",
    "res.checks": "Contrôles",
    "res.model": "Modèle",
    "res.page": "p.",
    "res.no_answer": "Pas de réponse",
    "res.failed": "La requête a échoué.",
    "dialog.close": "Fermer",
    "dialog.alt": "Page du contrat avec le passage cité surligné",
    "eval.loading": "Chargement…",
    "eval.unavailable": "Le rapport d'évaluation n'est pas encore disponible.",
    "eval.title": "Évaluation",
    "eval.intro": "{n} sinistres annotés à la main sur les trois contrats, avec le verdict attendu et la clause qui doit être citée. Lancé le {d} avec <code>{m}</code>. Commande : <code>uv run sinistres eval</code>.",
    "eval.m.acc": "Verdicts acceptables",
    "eval.m.clause": "Clause attendue citée",
    "eval.m.cit": "Citations retrouvées mot pour mot",
    "eval.m.abst": "« Indéterminé » quand il le fallait",
    "eval.m.wrong": "Verdicts assurés et faux",
    "eval.th": ["Cas", "Contrat", "Sinistre", "Attendu", "Obtenu", "Clause", "Citations"],
    "eval.note": "Les verdicts attendus supposent la garantie optionnelle concernée souscrite, comme le système. Quand le texte se prête à deux lectures, plusieurs verdicts sont acceptés. Un « indéterminé » sur un cas tranché compte comme une erreur, mais pas comme une erreur assurée.",
  },
  en: {
    "meta.title": "Covered or not?",
    "h1": "Covered or not?",
    "tagline": "Describe a claim. The system reads the general conditions, answers <em>covered</em>, <em>not covered</em> or <em>undetermined</em>, and shows the clauses it relies on.",
    "tab.analyse": "Analysis",
    "tab.methode": "How it's built",
    "tab.evaluation": "Evaluation",
    "notice": "Demo built for a recruitment exercise. Public contracts downloaded from the insurers' websites; personal project, not affiliated with the insurers cited. Not legal advice: only your policy schedule (Conditions Particulières) and your insurer are authoritative.",
    "form.contract": "The contract",
    "form.claim": "The claim",
    "form.claim_label": "Claim description",
    "form.placeholder": "E.g.: My bike was stolen from the building's shared bike room, which was not locked.",
    "form.examples": "Examples:",
    "form.submit": "Analyse the claim",
    "form.running": "Analysing…",
    "form.too_short": "Describe the claim in one or two sentences (at least 15 characters).",
    "ph.title": "The answer will appear here",
    "ph.li1": "<b>A verdict</b>: covered, not covered, or undetermined when the contract does not settle it.",
    "ph.li2": "<b>The cited clauses</b>, copied from the contract, with page and section, highlighted in the PDF.",
    "ph.li3": "<b>What would decide it</b>: missing facts and the guarantees to check in your policy schedule.",
    "loading.title": "Analysing…",
    "loading.s1": "Reading the claim (perils, property, terms)",
    "loading.s2": "Retrieving clauses from the database",
    "loading.s3": "Findings, citation checks and verdict",
    "loading.time": "About 10 to 30 seconds (small model, free tier).",
    "contract.version": "Version",
    "contract.pages": "pages",
    "contract.clauses": "clauses",
    "contract.source": "source PDF",
    "contract.error": "The contracts did not load. Reload the page in a moment.",
    "verdict.couvert": "Covered",
    "verdict.non_couvert": "Not covered",
    "verdict.indetermine": "Undetermined",
    "role.garantie": "Guarantee",
    "role.exclusion": "Exclusion",
    "role.condition": "Condition",
    "role.definition": "Definition",
    "role.limite": "Limit",
    "finding.garantie": "A guarantee applies",
    "finding.exclusion": "An exclusion applies",
    "finding.condition_non_remplie": "A condition is not met",
    "finding.oui": "yes",
    "finding.non": "no",
    "finding.incertain": "uncertain",
    "res.qualification": "How the facts are classified:",
    "res.downgraded": "The findings led to “{v}”, but that verdict did not rest on a verified clause: it was downgraded.",
    "res.missing": "What would decide it",
    "res.missing_none": "No missing fact reported.",
    "res.options": "To check in your policy schedule",
    "res.options_none": "No optional guarantee involved.",
    "res.clauses": "Clauses the answer rests on ({n})",
    "res.clauses_none": "No clause cited.",
    "res.verified": "✓ citation verified",
    "res.verified_title": "Found word for word in the contract text",
    "res.unverified": "⚠ citation not found",
    "res.unverified_title": "These words were not found in the clause: the step is ignored",
    "res.proposed": "Citation proposed by the model:",
    "res.see_pdf": "Show in the PDF",
    "res.trace": "How the answer was built",
    "res.perils": "Perils detected",
    "res.terms": "Terms searched",
    "res.read": "Clauses read",
    "res.read_n": "{a} of the contract's {b} clauses",
    "res.checks": "Checks",
    "res.model": "Model",
    "res.page": "p.",
    "res.no_answer": "No answer",
    "res.failed": "The request failed.",
    "dialog.close": "Close",
    "dialog.alt": "Contract page with the cited passage highlighted",
    "eval.loading": "Loading…",
    "eval.unavailable": "The evaluation report is not available yet.",
    "eval.title": "Evaluation",
    "eval.intro": "{n} claims labelled by hand on the three contracts, with the expected verdict and the clause that must be cited. Run on {d} with <code>{m}</code>. Command: <code>uv run sinistres eval</code>.",
    "eval.m.acc": "Acceptable verdicts",
    "eval.m.clause": "Expected clause cited",
    "eval.m.cit": "Citations found word for word",
    "eval.m.abst": "“Undetermined” when it should be",
    "eval.m.wrong": "Confident and wrong",
    "eval.th": ["Case", "Contract", "Claim", "Expected", "Got", "Clause", "Citations"],
    "eval.note": "Expected verdicts assume the relevant optional guarantee is subscribed, as the system does. When the text allows two readings, several verdicts are accepted. “Undetermined” on a settled case counts as an error, but not as a confident one.",
  },
};

const LANGS = ["fr", "en"];

function currentLang() {
  let saved = null;
  try { saved = localStorage.getItem("lang"); } catch { /* storage may be blocked */ }
  // French by default (the audience and the contracts are French); the switch is remembered.
  return LANGS.includes(saved) ? saved : "fr";
}

let LANG = currentLang();

function t(key, vars = {}) {
  const s = I18N[LANG][key] ?? I18N.fr[key] ?? key;
  return typeof s === "string" ? s.replace(/\{(\w+)\}/g, (_, k) => vars[k] ?? "") : s;
}

function applyStaticI18n() {
  document.documentElement.lang = LANG;
  document.title = t("meta.title");
  for (const el of document.querySelectorAll("[data-i18n]")) el.textContent = t(el.dataset.i18n);
  for (const el of document.querySelectorAll("[data-i18n-html]")) el.innerHTML = t(el.dataset.i18nHtml);
  for (const el of document.querySelectorAll("[data-i18n-attr]")) {
    for (const pair of el.dataset.i18nAttr.split(";")) {
      const [attr, key] = pair.split(":");
      el.setAttribute(attr, t(key));
    }
  }
  for (const b of document.querySelectorAll(".lang-switch button")) b.setAttribute("aria-pressed", String(b.dataset.lang === LANG));
}

function setLang(lang) {
  LANG = lang;
  try { localStorage.setItem("lang", lang); } catch { /* storage may be blocked */ }
  applyStaticI18n();
  document.dispatchEvent(new CustomEvent("langchange"));
}

"use strict";

// The "How it's built" diagrams, drawn as inline SVG. Each label is {fr, en} so one drawing serves both
// languages; renderDiagrams() runs again when the language changes.

const L = (fr, en) => (LANG === "en" ? en : fr);
const xesc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

function txt(x, y, s, cls = "s", anchor = "middle") {
  return `<text x="${x}" y="${y}" class="${cls}" text-anchor="${anchor}">${xesc(s)}</text>`;
}

// A box with a bold first line and smaller lines under it, centred.
function box(x, y, w, h, kind, lines, opts = {}) {
  const cx = x + w / 2;
  const gap = opts.gap || 16;
  const top = y + h / 2 - ((lines.length - 1) * gap) / 2 + 4;
  const body = lines.map((l, i) => txt(cx, top + i * gap, l, i === 0 ? "t" : opts.mono ? "m" : "s")).join("");
  return `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="9" class="b-${kind}"/>${body}`;
}

// Left-aligned box (records, tables): title bar then rows.
function table(x, y, w, title, rows, kind = "store") {
  const h = 30 + rows.length * 17 + 8;
  const r = rows.map((row, i) => txt(x + 12, y + 46 + i * 17, row, "m", "start")).join("");
  return `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="9" class="b-${kind}"/>
    <line x1="${x}" y1="${y + 28}" x2="${x + w}" y2="${y + 28}" class="sep"/>
    ${txt(x + 12, y + 19, title, "t", "start")}${r}`;
}

function edge(id, d, label, lx, ly, cls = "edge", anchor = "middle") {
  return `<path d="${d}" class="${cls}" marker-end="url(#ah-${id})"/>${label ? txt(lx, ly, label, "lbl", anchor) : ""}`;
}

function svg(id, w, h, aria, body) {
  return `<svg viewBox="0 0 ${w} ${h}" class="dg" role="img" aria-label="${xesc(aria)}">
    <defs><marker id="ah-${id}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0,0 L10,5 L0,10 z" class="ah"/></marker></defs>${body}</svg>`;
}

function legend(x, y) {
  const item = (dx, kind, label) =>
    `<rect x="${x + dx}" y="${y - 11}" width="22" height="14" rx="4" class="b-${kind}"/>${txt(x + dx + 30, y, label, "s", "start")}`;
  return item(0, "llm", L("appel au modèle (Mistral)", "model call (Mistral)"))
    + item(230, "code", L("code Python, déterministe", "Python code, deterministic"))
    + item(460, "store", L("données stockées", "stored data"));
}

/* ---------------------------------------------------------------- 1. two phases */

function dgOverview() {
  const id = "ov";
  const b1 = [10, 200, 390, 580, 770];
  const top = [
    ["code", L("PDF public", "Public PDF"), L("téléchargé, sha256", "downloaded, sha256"), L("vérifié", "checked")],
    ["code", L("Lignes", "Lines"), L("texte + page + position", "text + page + position"), L("2 colonnes, en-têtes", "2 columns, headers")],
    ["llm", L("Plan + clauses", "Outline + clauses"), L("le modèle renvoie", "the model returns"), L("des numéros de ligne", "line numbers only")],
    ["llm", L("Étiquettes", "Labels"), L("type + périls", "kind + perils"), L("vocabulaire commun", "shared vocabulary")],
    ["store", "SQLite", L("2 229 clauses", "2,229 clauses"), L("+ index plein texte", "+ full-text index")],
  ];
  let body = txt(10, 22, L("1 · UNE FOIS PAR CONTRAT — quelques minutes, ~150 appels au modèle",
    "1 · ONCE PER CONTRACT — a few minutes, ~150 model calls"), "lane", "start");
  top.forEach(([k, ...ls], i) => { body += box(b1[i], 36, 170, 78, k, ls); });
  for (let i = 0; i < 4; i++) body += edge(id, `M${b1[i] + 172} 75 H${b1[i + 1] - 4}`, "", 0, 0);

  const b2 = [10, 167, 324, 481, 638, 795];
  const bottom = [
    ["io", L("Récit du sinistre", "Claim story"), L("en français", "in French"), L("ou en anglais", "or in English")],
    ["llm", L("Faits", "Facts"), L("périls, biens,", "perils, property,"), L("termes à chercher", "terms to look up")],
    ["code", L("Recherche SQL", "SQL retrieval"), L("60–80 clauses", "60–80 clauses"), L("sur 500–900", "out of 500–900")],
    ["llm", L("Constats", "Findings"), L("3 × oui / non /", "3 × yes / no /"), L("incertain + citations", "uncertain + citations")],
    ["code", L("Contrôles + règle", "Checks + rule"), L("citations mot à mot,", "verbatim citations,"), L("verdict déduit", "verdict derived")],
    ["io", L("Réponse", "Answer"), L("verdict + clauses", "verdict + clauses"), L("surlignées dans le PDF", "highlighted in the PDF")],
  ];
  body += txt(10, 182, L("2 · À CHAQUE SINISTRE — environ 20 s, 2 appels au modèle", "2 · FOR EACH CLAIM — about 20 s, 2 model calls"), "lane", "start");
  bottom.forEach(([k, ...ls], i) => { body += box(b2[i], 196, 150, 78, k, ls); });
  for (let i = 0; i < 5; i++) body += edge(id, `M${b2[i] + 152} 235 H${b2[i + 1] - 4}`, "", 0, 0);

  // The store feeds retrieval and the highlight.
  body += edge(id, `M855 116 V150 H399 V192`, L("lit les clauses", "reads clauses"), 560, 144);
  body += edge(id, `M905 116 V192`, "", 0, 0, "edge dashed");
  body += txt(898, 172, L("positions des lignes", "line positions"), "lbl", "end");
  body += legend(10, 312);
  return svg(id, 960, 325, L("Deux phases : chaque contrat est préparé une fois en base, puis chaque sinistre est une requête et deux appels au modèle.",
    "Two phases: each contract is prepared once into a database, then each claim is a query and two model calls."), body);
}

/* ---------------------------------------------------------------- 2. the model points, it does not rewrite */

function dgSegment() {
  const id = "sg";
  let body = "";
  // PDF page
  body += `<rect x="10" y="30" width="330" height="200" rx="6" class="b-io"/>`;
  body += txt(10, 20, L("Page 16 du PDF, lignes numérotées", "PDF page 16, numbered lines"), "lane", "start");
  const page = [
    ["1260", "Sont exclus :", true],
    ["1261", "La simple perte ou la disparition d'objets,", false],
    ["1262", "l'usage abusif de chèques non libellés…", false],
    ["1263", "bancaires,", false],
    ["1264", "les vols d'animaux,", false],
    ["1265", "les vols des biens situés à l'extérieur…", false],
    ["1266", "assurés ou dans des locaux non clos,", false],
    ["1267", "…", false],
  ];
  page.forEach(([n, s, bold], i) => {
    const y = 56 + i * 22;
    body += txt(24, y, n, "m num", "start") + txt(70, y, s, bold ? "t small" : "s", "start");
  });
  body += `<rect x="64" y="${56 + 1 * 22 - 15}" width="270" height="${7 * 22}" rx="4" class="hl"/>`;

  // Model
  body += box(400, 60, 190, 140, "llm", [
    L("Le modèle répond", "The model answers"),
    "headings: [1260]",
    "clauses: [1261–1272]",
    "kind: exclusion",
    "perils: vol_vandalisme,",
    "  objets_valeur…",
  ], { mono: true, gap: 19 });
  body += edge(id, "M342 130 H396", L("lignes", "lines"), 369, 122);

  // Stored row
  body += table(650, 40, 300, L("Ligne de la table clauses", "Row of the clauses table"), [
    "id       baloise-home-2024:0164",
    "page     16",
    "section  … › Déchéance de la garantie",
    "         › Sont exclus :",
    "kind     exclusion",
    "perils   vol_vandalisme, objets_valeur…",
    L("text     ← lignes 1261–1272 du PDF", "text     ← PDF lines 1261–1272"),
  ]);
  body += edge(id, "M592 130 H646", L("numéros", "numbers"), 619, 122);
  // Text copied by code, bypassing the model
  body += edge(id, "M175 232 V262 H800 V202", L("le texte est recopié du PDF par le code, jamais par le modèle",
    "the text is copied from the PDF by the code, never by the model"), 488, 254, "edge strong");
  return svg(id, 960, 272, L("Le modèle ne renvoie que des numéros de ligne et des étiquettes ; le texte de chaque clause est recopié du PDF par le code.",
    "The model only returns line numbers and labels; each clause's text is copied from the PDF by the code."), body);
}

/* ---------------------------------------------------------------- 3. data model */

function dgSchema() {
  const id = "sc";
  let body = "";
  body += table(10, 20, 250, "contracts", [
    "id", "insurer, product", "version, effective", "url, sha256", "n_pages, n_clauses",
  ]);
  body += table(330, 20, 260, "clauses", [
    "id, contract_id", "start_n … end_n", "page_start, page_end", "section_path, title", "kind, defined_term", "text",
  ]);
  body += table(710, 20, 240, "lines", [
    "contract_id, n", "page, text", "x0, y0, x1, y1",
  ]);
  body += table(710, 150, 240, "clause_perils", ["clause_id", "peril"]);
  body += table(330, 200, 260, "clauses_fts (FTS5, BM25)", ["text, title, section_path"], "code");

  body += edge(id, "M262 70 H326", "1 — n", 294, 62);
  body += edge(id, "M592 60 H706", "start_n … end_n", 649, 52);
  body += txt(649, 78, L("→ surlignage", "→ highlight"), "lbl");
  body += edge(id, "M592 150 H640 V190 H706", "1 — n", 673, 183);
  body += edge(id, "M460 152 V196", L("indexé", "indexed"), 470, 180, "edge", "start");
  return svg(id, 960, 262, L("Schéma : un contrat a des lignes et des clauses ; chaque clause a ses périls et une entrée plein texte.",
    "Schema: a contract has lines and clauses; each clause has its perils and a full-text entry."), body);
}

/* ---------------------------------------------------------------- 4. retrieval */

function dgRetrieval() {
  const id = "rt";
  let body = "";
  body += box(10, 70, 170, 110, "store", [L("Clauses du contrat", "Contract clauses"), L("500 à 900", "500 to 900"), L("étiquetées", "labelled")]);
  const src = [
    [20, L("Texte", "Text"), L("BM25 sur les termes du sinistre", "BM25 on the claim's terms"), "MATCH … ORDER BY bm25 LIMIT 25"],
    [100, L("Structure", "Structure"), L("garanties, exclusions, conditions, limites", "guarantees, exclusions, conditions, limits"), L("JOIN clause_perils ON périls du sinistre", "JOIN clause_perils ON the claim's perils")],
    [180, L("Général", "General"), L("exclusions et conditions communes", "exclusions and conditions for all covers"), "peril = 'general'"],
  ];
  src.forEach(([y, a, b, c]) => {
    body += box(250, y, 300, 68, "code", [a, b, c], { gap: 17 });
    body += edge(id, `M182 125 C215 125 215 ${y + 34} 246 ${y + 34}`, "", 0, 0);
    body += edge(id, `M552 ${y + 34} C585 ${y + 34} 585 145 616 145`, "", 0, 0);
  });
  body += box(620, 105, 150, 80, "code", [L("Union ordonnée", "Ordered union"), L("sans doublon,", "no duplicates,"), L("60 au plus", "60 at most")]);
  body += box(810, 30, 140, 70, "code", [L("Définitions", "Definitions"), L("des termes présents", "of the terms used"), L("20 au plus", "20 at most")]);
  body += edge(id, "M880 102 V140 H774", "", 0, 0);
  body += box(810, 170, 140, 80, "llm", [L("Envoyé au modèle", "Sent to the model"), L("≈ 60–80 clauses", "≈ 60–80 clauses"), L("avec page, section", "with page, section")]);
  body += edge(id, "M772 160 H790 V210 H806", "", 0, 0);
  return svg(id, 960, 262, L("Recherche : trois requêtes SQL (texte, structure, général) puis les définitions ; 60 à 80 clauses sur 500 à 900 vont au modèle.",
    "Retrieval: three SQL queries (text, structure, general) then definitions; 60 to 80 of 500 to 900 clauses reach the model."), body);
}

/* ---------------------------------------------------------------- 5. decision */

function dgDecision() {
  const id = "dc";
  let body = "";
  body += box(10, 30, 180, 110, "llm", [
    L("Le modèle (appel 2)", "The model (call 2)"),
    L("citations", "citations"),
    L("garantie : oui/non/?", "guarantee: yes/no/?"),
    L("exclusion : … + mots du récit", "exclusion: … + claim words"),
    L("condition : … + mots du récit", "condition: … + claim words"),
  ], { gap: 18 });

  body += box(230, 40, 200, 90, "code", [L("Citation trouvée", "Citation found"), L("mot pour mot dans", "word for word in"), L("la clause citée ?", "the cited clause?")]);
  body += box(470, 40, 200, 90, "code", [L("Doute appuyé sur", "Doubt backed by"), L("des mots du récit ?", "words of the claim?"), L("(exclusion, condition)", "(exclusion, condition)")]);
  body += box(710, 22, 240, 126, "code", [
    L("Règle de décision", "Decision rule"),
    L("garantie = non, ou", "guarantee = no, or"),
    L("exclusion / condition = oui", "exclusion / condition = yes"),
    L("  → non couvert", "  → not covered"),
    L("garantie = oui et rien contre", "guarantee = yes, nothing against"),
    L("  → couvert ; sinon indéterminé", "  → covered; else undetermined"),
  ], { gap: 17 });
  body += edge(id, "M192 85 H226", "", 0, 0);
  body += edge(id, "M432 85 H466", L("oui", "yes"), 449, 77);
  body += edge(id, "M672 85 H706", L("oui", "yes"), 689, 77);

  // Rejections
  body += box(240, 150, 180, 46, "note", [L("ignorée, affichée ⚠", "ignored, shown ⚠"), L("ne compte pas", "does not count")]);
  body += edge(id, "M330 132 V146", L("non", "no"), 340, 143, "edge", "start");
  body += box(480, 150, 180, 46, "note", [L("constat → non", "finding → no"), L("présomption de bonne foi", "presumed compliance")]);
  body += edge(id, "M570 132 V146", L("non", "no"), 580, 143, "edge", "start");

  // Final gate
  body += box(710, 206, 240, 80, "code", [L("La clause décisive", "Is the deciding clause"), L("est-elle citée", "cited and"), L("et vérifiée ?", "verified?")]);
  body += edge(id, "M830 150 V202", "", 0, 0);
  body += box(450, 212, 200, 68, "io", [L("Verdict", "Verdict"), L("couvert / non couvert", "covered / not covered"), L("/ indéterminé", "/ undetermined")]);
  body += edge(id, "M708 246 H654", L("oui", "yes"), 681, 238);
  body += box(160, 302, 240, 50, "io", [L("Indéterminé", "Undetermined"), L("avec la raison affichée", "with the reason shown")]);
  body += edge(id, "M830 288 V327 H404", L("non : rétrogradé", "no: downgraded"), 610, 319);
  return svg(id, 960, 362, L("Décision : le modèle donne des constats ; le code vérifie citations et faits, applique la règle, et rétrograde en indéterminé ce qui n'est pas sourcé.",
    "Decision: the model gives findings; the code checks citations and facts, applies the rule, and downgrades unsourced verdicts to undetermined."), body);
}

function renderDiagrams() {
  const map = { "dg-overview": dgOverview, "dg-segment": dgSegment, "dg-schema": dgSchema, "dg-retrieval": dgRetrieval, "dg-decision": dgDecision };
  for (const [elId, fn] of Object.entries(map)) {
    const el = document.getElementById(elId);
    if (el) el.innerHTML = fn();
  }
}

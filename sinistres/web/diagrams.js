"use strict";

// The two animated diagrams of "How it's built". Each is an SVG plus a stepper: one step lights up at a
// time, with a caption under the drawing. Labels are {fr, en}; renderDiagrams() runs again on language
// change. With prefers-reduced-motion the steppers do not auto-play.

const L = (fr, en) => (LANG === "en" ? en : fr);
const xesc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const txt = (x, y, s, cls, anchor = "middle") =>
  `<text x="${x}" y="${y}" class="${cls}" text-anchor="${anchor}">${xesc(s)}</text>`;

const timers = [];
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

function marker(id) {
  return `<defs><marker id="ah-${id}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
    <path d="M0,0 L10,5 L0,10 z" class="ah"/></marker></defs>`;
}

// A card node: number badge, title, one short line. `steps` lists the stepper states that light it up.
function node(steps, x, y, w, h, kind, n, title, sub) {
  return `<g class="node ${kind}" data-step="${steps}">
    <rect x="${x}" y="${y}" width="${w}" height="${h}" rx="14"/>
    <circle cx="${x + 22}" cy="${y + 22}" r="11" class="badge-c"/>
    ${txt(x + 22, y + 26, n, "badge-t")}
    ${txt(x + 42, y + 27, title, "n-title", "start")}
    ${txt(x + 16, y + h - 16, sub, "n-sub", "start")}
  </g>`;
}

/* ---------------------------------------------------------------- stepper */

function stepper(root, steps, apply) {
  const caption = root.querySelector(".dg-caption");
  const dots = root.querySelector(".dg-dots");
  const play = root.querySelector(".dg-play");
  const prev = root.querySelector(".dg-prev");
  const next = root.querySelector(".dg-next");
  dots.innerHTML = steps.map((_, i) => `<button type="button" aria-label="${i + 1}" data-i="${i}"></button>`).join("");
  let i = 0;
  let playing = !reducedMotion;

  function show(k) {
    i = (k + steps.length) % steps.length;
    apply(i);
    caption.innerHTML = `<b>${i + 1}.</b> ${xesc(steps[i])}`;
    for (const d of dots.children) d.classList.toggle("on", Number(d.dataset.i) === i);
  }
  function setPlaying(p) {
    playing = p;
    play.textContent = playing ? "❚❚" : "▶";
    play.setAttribute("aria-label", playing ? L("Pause", "Pause") : L("Lecture", "Play"));
  }
  dots.onclick = (e) => {
    const b = e.target.closest("button");
    if (b) { setPlaying(false); show(Number(b.dataset.i)); }
  };
  play.onclick = () => setPlaying(!playing);
  // Manual stepping: any manual move pauses the animation.
  prev.onclick = () => { setPlaying(false); show(i - 1); };
  next.onclick = () => { setPlaying(false); show(i + 1); };
  root.onkeydown = (e) => {
    if (e.key === "ArrowRight") { e.preventDefault(); next.onclick(); }
    if (e.key === "ArrowLeft") { e.preventDefault(); prev.onclick(); }
  };
  prev.setAttribute("aria-label", L("Étape précédente", "Previous step"));
  next.setAttribute("aria-label", L("Étape suivante", "Next step"));
  timers.push(setInterval(() => { if (playing && !document.hidden) show(i + 1); }, 3000));
  setPlaying(playing);
  show(0);
}

/* ---------------------------------------------------------------- 1. the journey of a question */

const J = [[95, 108], [290, 108], [485, 108], [680, 108], [680, 238], [680, 108], [875, 108]];

function journeySvg() {
  const id = "jr";
  let b = marker(id);
  b += node("0", 20, 65, 150, 86, "io", "1", L("Le sinistre", "The claim"), L("français ou anglais", "French or English"));
  b += node("1", 215, 65, 150, 86, "code", "2", L("Recherche", "Retrieval"), L("60–80 clauses sur 900", "60–80 of 900 clauses"));
  b += node("2", 410, 65, 150, 86, "llm", "3", "Gemini", L("constats + citations", "findings + citations"));
  b += node("3 5", 605, 65, 150, 86, "code", "4", L("Contrôles", "Checks"), L("citations, règle", "citations, rule"));
  b += node("4", 605, 200, 150, 76, "strong", "5", L("Relecture", "Review"), L("chaque refus, à part", "every denial, apart"));
  b += node("6", 800, 65, 150, 86, "out", "6", "Verdict", L("+ clauses surlignées", "+ highlighted clauses"));

  for (const x of [172, 367, 562, 757]) b += `<path d="M${x} 108 H${x + 39}" class="edge" marker-end="url(#ah-${id})"/>`;
  b += `<path d="M655 153 V196" class="edge dashed" marker-end="url(#ah-${id})"/>`;
  b += `<path d="M705 198 V155" class="edge dashed" marker-end="url(#ah-${id})"/>`;
  b += txt(645, 180, L("si refus", "if denial"), "e-lbl", "end");
  b += txt(715, 180, L("confirmé ou non", "upheld or not"), "e-lbl", "start");

  // The database the retrieval reads, prepared once (second diagram).
  b += `<g class="db"><path d="M244 20 V40 A46 9 0 0 0 336 40 V20"/><ellipse cx="290" cy="20" rx="46" ry="9"/></g>`;
  b += txt(346, 34, L("2 229 clauses, préparées une fois", "2,229 clauses, prepared once"), "e-lbl", "start");
  b += `<path d="M290 51 V61" class="edge" marker-end="url(#ah-${id})"/>`;

  b += `<circle r="8" class="token" style="transform: translate(${J[0][0]}px, ${J[0][1] + 52}px)"/>`;
  return `<svg viewBox="0 0 970 290" class="dg dg-anim" role="img" aria-label="${xesc(L(
    "Le parcours d'une question : sinistre, recherche en base, Gemini, contrôles, relecture des refus, verdict.",
    "The path of a question: claim, database retrieval, Gemini, checks, review of denials, verdict."))}">${b}</svg>`;
}

function journeySteps() {
  return [
    L("Vous décrivez le sinistre, en français ou en anglais.", "You describe the claim, in French or in English."),
    L("La base trouve les 60 à 80 clauses utiles parmi 500 à 900 : les mots du sinistre et leurs synonymes, le chapitre du péril, les exclusions générales, les définitions.",
      "The database finds the 60 to 80 useful clauses out of 500 to 900: the claim's words and their synonyms, the peril's chapter, the general exclusions, the definitions."),
    L("Gemini lit seulement ces clauses et répond à trois questions (une garantie ? une exclusion ? une condition non remplie ?) en citant le texte.",
      "Gemini reads only these clauses and answers three questions (a guarantee? an exclusion? an unmet condition?) quoting the text."),
    L("Le code vérifie chaque citation mot pour mot dans le contrat, puis applique une règle de décision écrite à l'avance.",
      "The code checks every quote word for word in the contract, then applies a decision rule written in advance."),
    L("Un refus est relu à part : la clause citée s'applique-t-elle vraiment aux faits, et contient-elle une exception (« sauf… ») ?",
      "A denial is reviewed separately: does the cited clause really apply to the facts, and does it contain an exception (“sauf…”)?"),
    L("Si la relecture ne confirme pas le refus, la réponse devient « indéterminé » plutôt qu'un refus non fondé.",
      "If the review does not uphold the denial, the answer becomes “undetermined” rather than an unfounded refusal."),
    L("Le verdict s'affiche avec les clauses citées, surlignées dans le PDF, ou « indéterminé » avec ce qui manque pour trancher.",
      "The verdict is shown with the cited clauses, highlighted in the PDF, or “undetermined” with what is missing to decide."),
  ];
}

function applyJourney(root, i) {
  for (const g of root.querySelectorAll(".node")) g.classList.toggle("on", g.dataset.step.split(" ").includes(String(i)));
  const [x, y] = J[i];
  root.querySelector(".token").style.transform = `translate(${x}px, ${y + 52}px)`;
}

/* ---------------------------------------------------------------- 2. preparing a contract, once */

function prepareSvg() {
  const id = "pp";
  let b = marker(id);
  // An abstract PDF page: grey bars of text.
  b += `<rect x="20" y="16" width="300" height="226" rx="12" class="page"/>`;
  b += txt(34, 40, L("PDF, page 16", "PDF, page 16"), "e-lbl", "start");
  [120, 240, 210, 180, 230, 200, 150].forEach((w, k) => {
    const y = 58 + k * 24;
    b += `<rect x="62" y="${y}" width="${w}" height="9" rx="4.5" class="${k === 0 ? "bar head" : "bar"}"/>`;
    b += `<g class="layer l1">${txt(48, y + 9, String(k + 1), "num", "end")}</g>`;
  });
  // The model marks heading and clauses, by line number.
  b += `<g class="layer l2">
    <rect x="56" y="52" width="252" height="21" rx="6" class="mark-h"/>
    <rect x="56" y="76" width="252" height="69" rx="6" class="mark-c"/>
    <rect x="56" y="148" width="252" height="69" rx="6" class="mark-c"/>
    <path d="M322 129 H386" class="edge" marker-end="url(#ah-${id})"/>
    ${txt(354, 121, L("lignes", "lines"), "e-lbl")}
    <rect x="390" y="88" width="180" height="82" rx="14" class="chip"/>
    ${txt(480, 114, L("Le modèle", "The model"), "n-title")}
    ${txt(480, 137, L("titre : 1", "heading: 1"), "mono")}
    ${txt(480, 156, L("clauses : 2–4, 5–7", "clauses: 2–4, 5–7"), "mono")}
  </g>`;
  // The clauses table.
  b += `<g class="layer l3">
    <path d="M572 129 H616" class="edge" marker-end="url(#ah-${id})"/>
    ${txt(594, 121, L("numéros", "numbers"), "e-lbl")}
    <rect x="620" y="30" width="330" height="190" rx="14" class="table"/>
    ${txt(640, 56, L("Table des clauses", "Clauses table"), "n-title", "start")}
    <g class="row r1"><rect x="636" y="70" width="298" height="62" rx="10" class="rowbg"/>
      <rect x="648" y="82" width="74" height="19" rx="5" class="tag-ex"/>${txt(685, 96, "Exclusion", "tag-t")}
      ${txt(732, 96, L("vol · p.16 · lignes 2–4", "theft · p.16 · lines 2–4"), "n-sub", "start")}
      <rect x="648" y="112" width="230" height="7" rx="3.5" class="bar"/></g>
    <g class="row r2"><rect x="636" y="142" width="298" height="62" rx="10" class="rowbg"/>
      <rect x="648" y="154" width="74" height="19" rx="5" class="tag-ex"/>${txt(685, 168, "Exclusion", "tag-t")}
      ${txt(732, 168, L("objets de valeur · lignes 5–7", "valuables · lines 5–7"), "n-sub", "start")}
      <rect x="648" y="184" width="200" height="7" rx="3.5" class="bar"/></g>
    <path d="M170 244 C 170 270, 785 270, 785 224" class="edge strong" marker-end="url(#ah-${id})"/>
    ${txt(478, 254, L("le texte est recopié du PDF par le code, jamais réécrit par le modèle",
      "the text is copied from the PDF by the code, never rewritten by the model"), "e-lbl")}
  </g>`;
  return `<svg viewBox="0 0 970 280" class="dg dg-anim" data-stage="0" role="img" aria-label="${xesc(L(
    "Préparer un contrat : les lignes du PDF sont numérotées, le modèle indique où sont les clauses, le code les range en base avec le texte du PDF.",
    "Preparing a contract: PDF lines are numbered, the model says where the clauses are, the code stores them with the PDF's text."))}">${b}</svg>`;
}

function prepareSteps() {
  return [
    L("Le PDF est lu ligne par ligne : chaque ligne garde sa page et sa position, pour pouvoir la surligner plus tard.",
      "The PDF is read line by line: each line keeps its page and position, so it can be highlighted later."),
    L("Un modèle indique seulement où commencent et finissent les titres et les clauses : des numéros de ligne, rien d'autre.",
      "A model only says where headings and clauses start and end: line numbers, nothing else."),
    L("Le code recopie le texte depuis le PDF et range chaque clause avec son type, ses périls et sa page. C'est fait une seule fois par contrat.",
      "The code copies the text from the PDF and stores each clause with its kind, perils and page. This is done once per contract."),
  ];
}

function applyPrepare(root, i) {
  root.querySelector("svg").dataset.stage = String(i);
}

/* ---------------------------------------------------------------- render */

function figure(svg) {
  return `${svg}
    <div class="dg-controls">
      <button type="button" class="dg-play"></button>
      <div class="dg-dots"></div>
      <div class="dg-nav">
        <button type="button" class="dg-prev">‹ ${L("Précédent", "Previous")}</button>
        <button type="button" class="dg-next">${L("Suivant", "Next")} ›</button>
      </div>
    </div>
    <p class="dg-caption" aria-live="polite"></p>`;
}

function renderDiagrams() {
  while (timers.length) clearInterval(timers.pop());
  const journey = document.getElementById("dg-journey");
  if (journey) {
    journey.innerHTML = figure(journeySvg());
    stepper(journey, journeySteps(), (i) => applyJourney(journey, i));
  }
  const prepare = document.getElementById("dg-prepare");
  if (prepare) {
    prepare.innerHTML = figure(prepareSvg());
    stepper(prepare, prepareSteps(), (i) => applyPrepare(prepare, i));
  }
}

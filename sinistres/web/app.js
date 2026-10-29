"use strict";

// Examples per language. English claims work too: the model reads them and searches the French text.
const EXAMPLES = {
  fr: [
    ["Vélo volé, local commun ouvert", "Mon vélo a été volé dans le local commun de l'immeuble, qui n'était pas fermé à clé."],
    ["Bougie fondue sur la table de jardin", "Pendant mes vacances, une bougie laissée sur la table de mon jardin a fondu avec la chaleur et a abîmé la table."],
    ["Fuite de la machine à laver", "Le tuyau de ma machine à laver a lâché et l'eau a abîmé le parquet du salon."],
    ["Ordinateur portable tombé", "J'ai fait tomber mon ordinateur portable par terre chez moi, l'écran est cassé."],
    ["Cave inondée par un orage", "Après un violent orage, l'eau de pluie est entrée dans ma cave et a abîmé les cartons qui y étaient stockés."],
    ["Bijoux volés, porte forcée", "Des cambrioleurs ont forcé la porte d'entrée de ma maison et ont volé mes bijoux pendant que j'étais au travail."],
  ],
  en: [
    ["Bike stolen, shared room unlocked", "My bike was stolen from the building's shared bike room, which was not locked."],
    ["Candle melted on the garden table", "While I was on holiday, a candle left on my garden table melted in the heat and damaged the table."],
    ["Washing machine leak", "The hose of my washing machine burst and the water damaged the living-room parquet."],
    ["Laptop dropped", "I dropped my laptop on the floor at home and the screen broke."],
    ["Cellar flooded by a storm", "After a violent storm, rainwater got into my cellar and damaged the boxes stored there."],
    ["Jewellery stolen, door forced", "Burglars forced the front door of my house and stole my jewellery while I was at work."],
  ],
};

const VERDICT_ICONS = { couvert: "✓", non_couvert: "✕", indetermine: "?" };

const $ = (sel) => document.querySelector(sel);
let state = { contracts: [], perils: {}, contractId: null, lastResult: null, lastContract: null, evalReport: null };

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// The model sometimes writes **bold** or *italics* in its prose: render them instead of showing stars.
function md(s) {
  return esc(s).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/\*(.+?)\*/g, "<i>$1</i>");
}

/* ---------------------------------------------------------------- tabs */

function showTab(name) {
  for (const el of document.querySelectorAll(".tab")) el.classList.toggle("active", el.dataset.tab === name);
  for (const p of document.querySelectorAll(".panel")) p.hidden = p.id !== `tab-${name}`;
  if (name === "evaluation") loadEval();
}
window.addEventListener("hashchange", () => showTab(location.hash.slice(1) || "analyse"));

/* ---------------------------------------------------------------- contracts and examples */

async function loadContracts(attempt = 0) {
  let data;
  try {
    const r = await fetch("/api/contracts");
    if (!r.ok) throw new Error(r.status);
    data = await r.json();
  } catch {
    // The server scales to zero and may still be starting: retry a few times before giving up.
    if (attempt < 5) return setTimeout(() => loadContracts(attempt + 1), 2000 * (attempt + 1));
    $("#contracts").innerHTML = `<p class="error">${esc(t("contract.error"))}</p>`;
    return;
  }
  state.contracts = data.contracts;
  state.perils = data.perils;
  state.contractId = state.contractId || data.contracts[0]?.id;
  renderContracts();
}

function renderContracts() {
  $("#contracts").innerHTML = state.contracts.map((c) => `
    <label class="contract${c.id === state.contractId ? " selected" : ""}">
      <input type="radio" name="contract" value="${esc(c.id)}" ${c.id === state.contractId ? "checked" : ""}>
      <span class="name">${esc(c.insurer)} — ${esc(c.product)}</span>
      <span class="meta">${t("contract.version")} ${esc(c.version)} · ${c.n_pages} ${t("contract.pages")} · ${c.n_clauses} ${t("contract.clauses")} ·
        <a href="${esc(c.url)}" target="_blank" rel="noopener">${t("contract.source")}</a></span>
    </label>`).join("");
}

$("#contracts").addEventListener("change", (e) => {
  state.contractId = e.target.value;
  renderContracts();
});

function renderExamples() {
  $("#examples").innerHTML = EXAMPLES[LANG]
    .map(([label], i) => `<button type="button" class="chip" data-i="${i}">${esc(label)}</button>`).join("");
}

$("#examples").addEventListener("click", (e) => {
  const b = e.target.closest(".chip");
  if (!b) return;
  $("#claim").value = EXAMPLES[LANG][b.dataset.i][1];
  $("#claim").focus();
});

/* ---------------------------------------------------------------- highlighting a citation inside its clause */

function markCitation(text, citation) {
  // The citation was checked server-side after normalising quotes and spaces; here the same words
  // are matched loosely (any punctuation or spacing between them) so they can be marked in place.
  const fragments = citation.split(/\.\.\.|…|\[\.\.\.\]/).map((f) => f.match(/[\p{L}\p{N}]+/gu) || []).filter((w) => w.length);
  const ranges = [];
  let from = 0;
  for (const words of fragments) {
    const re = new RegExp(words.map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("[^\\p{L}\\p{N}]{1,6}"), "giu");
    re.lastIndex = from;
    const m = re.exec(text);
    if (!m) continue;
    ranges.push([m.index, m.index + m[0].length]);
    from = m.index + m[0].length;
  }
  let out = "", pos = 0;
  for (const [a, b] of ranges) {
    out += esc(text.slice(pos, a)) + "<mark>" + esc(text.slice(a, b)) + "</mark>";
    pos = b;
  }
  return { html: out + esc(text.slice(pos)), excerpt: ranges.map(([a, b]) => text.slice(a, b)).join(" … ") };
}

/* ---------------------------------------------------------------- result */

function renderResult(r) {
  const v = r.verdict;
  const downgraded = r.verdict !== r.verdict_modele;
  const missing = r.informations_manquantes || [];
  const options = r.garanties_a_verifier || [];
  const perilLabels = state.perils[LANG] || state.perils.fr || {};

  const steps = r.etapes.map((s) => {
    const c = s.clause;
    const p = t("res.page");
    const pages = c.page_start === c.page_end ? `${p} ${c.page_start}` : `${p} ${c.page_start}–${c.page_end}`;
    const marked = s.verifiee ? markCitation(c.text, s.citation) : null;
    const quote = marked && marked.excerpt ? marked.excerpt : s.citation;
    return `
      <li class="card cite${s.verifiee ? "" : " unverified"}">
        <div class="cite-meta">
          <span class="role ${esc(s.role)}">${esc(t(`role.${s.role}`))}</span>
          <span>${pages}</span>
          <span class="where">${esc(c.section_path || "")}</span>
          <span class="check ${s.verifiee ? "ok" : "ko"}" title="${esc(t(s.verifiee ? "res.verified_title" : "res.unverified_title"))}">${t(s.verifiee ? "res.verified" : "res.unverified")}</span>
        </div>
        <blockquote class="quote" lang="fr">${esc(quote)}</blockquote>
        <p class="explication">${md(s.explication)}</p>
        <div class="cite-actions">
          <button type="button" class="text-btn" data-toggle>${t("res.full_clause")}</button>
          <button type="button" class="text-btn" data-page="${c.page_start}" data-lines="${(s.lignes || []).join(",")}"
            data-title="${esc(`${r.contract.insurer} — ${pages} — ${c.section_path}`)}">${t("res.see_pdf")}</button>
        </div>
        <div class="clause-text" lang="fr" hidden>${marked ? marked.html : esc(c.text)}</div>
      </li>`;
  }).join("");

  const perils = (r.analyse_sinistre.perils || []).map((x) => `<span class="tag">${esc(perilLabels[x] || x)}</span>`).join("");
  const termes = (r.analyse_sinistre.termes || []).map((x) => `<span class="tag">${esc(x)}</span>`).join("");
  const findings = r.constats ? ["garantie", "exclusion", "condition_non_remplie"]
    .map((k) => `<span class="f-${r.constats[k]}">${t(`finding.short.${k}`)}&nbsp;: <b>${t(`finding.${r.constats[k]}`)}</b></span>`).join("") : "";

  const decide = missing.length || options.length ? `
    <div class="card decide">
      ${missing.length ? `<h3>${t("res.missing")}</h3><ul>${missing.map((m) => `<li>${md(m)}</li>`).join("")}</ul>` : ""}
      ${options.length ? `<h3>${t("res.options")}</h3><ul>${options.map((m) => `<li>${md(m)}</li>`).join("")}</ul>` : ""}
    </div>` : "";

  $("#result").innerHTML = `
    <div class="card verdict ${v}">
      <div class="verdict-line">
        <span class="badge ${v}">${VERDICT_ICONS[v]} ${t(`verdict.${v}`)}</span>
        <span class="hint">${esc(r.contract.insurer)} — ${esc(r.contract.product)}</span>
      </div>
      <p class="resume">${md(r.resume)}</p>
      ${findings ? `<p class="findings">${findings}</p>` : ""}
      ${downgraded ? `<p class="downgraded">${esc(t("res.downgraded", { v: t(`verdict.${r.verdict_modele}`) }))}</p>` : ""}
    </div>
    ${decide}
    ${v === "indetermine" && r.examine ? examinedBox(r) : ""}
    <h3 class="section-title">${t("res.cited", { n: r.etapes.length })}</h3>
    ${steps ? `<ol class="cites">${steps}</ol>` : `<p class="hint">${t("res.clauses_none")}</p>`}

    <details class="card trace">
      <summary>${t("res.trace")}</summary>
      <dl class="kv">
        ${r.qualification ? `<dt>${t("res.qualification").replace(/[\s ]*:$/, "")}</dt><dd>${md(r.qualification)}</dd>` : ""}
        <dt>${t("res.perils")}</dt><dd>${perils}</dd>
        <dt>${t("res.terms")}</dt><dd>${termes}</dd>
        <dt>${t("res.read")}</dt><dd>${t("res.read_n", { a: r.clauses_lues.lues, b: r.clauses_lues.total })}</dd>
        <dt>${t("res.checks")}</dt><dd>${(r.controles || []).map((c) => esc(c)).join("<br>") || "—"}</dd>
        <dt>${t("res.model")}</dt><dd>${esc(r.modele)} · ${r.duree_s} s</dd>
      </dl>
    </details>`;
}

// An answer that cannot decide shows what it searched: the claim's terms, the clauses read by source,
// and the clauses it rests on.
function examinedBox(r) {
  const src = r.examine.sources || {};
  const parts = ["texte", "péril", "général", "définition"].filter((k) => src[k])
    .map((k) => t(`examined.src.${k}`, { n: src[k] }));
  return `
    <div class="card decide examined">
      <h3>${t("examined.title")}</h3>
      <p class="hint">${t("examined.body", { n: r.clauses_lues.lues, total: r.clauses_lues.total })}</p>
      <ul>${parts.map((p) => `<li>${p}</li>`).join("")}</ul>
      <p class="hint">${t("examined.terms")} ${(r.analyse_sinistre.termes || []).map((x) => `<span class="tag">${esc(x)}</span>`).join("")}</p>
    </div>`;
}

/* ---------------------------------------------------------------- PDF page dialog */

function openPage(btn) {
  const dlg = $("#page-dialog");
  $("#page-title").textContent = btn.dataset.title;
  $("#page-img").src = `/api/page/${encodeURIComponent(state.lastContract)}/${btn.dataset.page}.png?lines=${btn.dataset.lines}`;
  dlg.showModal();
  dlg.querySelector(".dialog-body").scrollTop = 0;
}

$("#page-close").addEventListener("click", () => $("#page-dialog").close());
$("#page-dialog").addEventListener("click", (e) => { if (e.target.id === "page-dialog") e.target.close(); });
$("#result").addEventListener("click", (e) => {
  const toggle = e.target.closest("[data-toggle]");
  if (toggle) {
    const box = toggle.closest(".cite").querySelector(".clause-text");
    box.hidden = !box.hidden;
    toggle.textContent = t(box.hidden ? "res.full_clause" : "res.hide_clause");
    return;
  }
  const b = e.target.closest("[data-page]");
  if (b) openPage(b);
});

/* ---------------------------------------------------------------- submit */

$("#form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const claim = $("#claim").value.trim();
  const err = $("#form-error");
  err.hidden = true;
  if (claim.length < 15) {
    err.textContent = t("form.too_short");
    err.hidden = false;
    return;
  }
  const btn = $("#submit");
  btn.disabled = true;
  btn.textContent = t("form.running");
  $("#result").innerHTML = $("#tpl-loading").innerHTML;
  applyStaticI18n();
  try {
    const r = await fetch("/api/analyse", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ contract_id: state.contractId, claim, lang: LANG }),
    });
    const data = await r.json();
    if (!r.ok) throw new Error(typeof data.detail === "string" ? data.detail : t("res.failed"));
    state.lastContract = data.contract.id;
    state.lastResult = data;
    renderResult(data);
    if (window.innerWidth < 900) $("#result").scrollIntoView({ behavior: "smooth" });
  } catch (ex) {
    $("#result").innerHTML = `<div class="card placeholder"><p class="loading-title">${t("res.no_answer")}</p><p class="error">${esc(ex.message)}</p></div>`;
  } finally {
    btn.disabled = false;
    btn.textContent = t("form.submit");
  }
});

/* ---------------------------------------------------------------- evaluation tab */

async function loadEval() {
  if (!state.evalReport) {
    state.evalReport = await (await fetch("/api/eval")).json();
  }
  renderEval();
}

function renderEval() {
  const r = state.evalReport;
  if (!r) return;
  if (r.available === false) {
    $("#eval").innerHTML = `<p class="muted">${t("eval.unavailable")}</p>`;
    return;
  }
  const m = r.metrics;
  const pct = (x) => (x == null ? "—" : `${Math.round(x * 100)} %`);
  const rows = r.cases.map((c) => `
    <tr>
      <td>${esc(c.id)}</td>
      <td>${esc(c.contract)}</td>
      <td lang="fr">${esc(c.claim)}</td>
      <td>${t(`verdict.${c.expected}`)}</td>
      <td class="${c.verdict_ok ? "ok-txt" : "ko-txt"}">${t(`verdict.${c.got}`)}</td>
      <td>${c.expected_clause_hit == null ? "—" : c.expected_clause_hit ? "✓" : "✕"}</td>
      <td>${c.citations_verified}/${c.citations_total}</td>
    </tr>`).join("");
  const th = t("eval.th").map((h) => `<th>${h}</th>`).join("");
  $("#eval").innerHTML = `
    <h2>${t("eval.title")}</h2>
    <p>${t("eval.intro", { n: r.cases.length, d: esc(r.run_at), m: esc(r.model) })}</p>
    <div class="metrics">
      <div class="metric"><div class="v">${pct(m.verdict_accuracy)}</div><div class="l">${t("eval.m.acc")}</div></div>
      <div class="metric"><div class="v">${pct(m.expected_clause_recall)}</div><div class="l">${t("eval.m.clause")}</div></div>
      <div class="metric"><div class="v">${pct(m.citation_verified_rate)}</div><div class="l">${t("eval.m.cit")}</div></div>
      <div class="metric"><div class="v">${pct(m.abstention_recall)}</div><div class="l">${t("eval.m.abst")}</div></div>
      <div class="metric"><div class="v">${pct(m.wrong_confident_rate)}</div><div class="l">${t("eval.m.wrong")}</div></div>
    </div>
    <div class="table-scroll"><table>
      <thead><tr>${th}</tr></thead>
      <tbody>${rows}</tbody>
    </table></div>
    <p class="muted small">${t("eval.note")}</p>`;
}

/* ---------------------------------------------------------------- language */

for (const b of document.querySelectorAll(".lang-switch button")) {
  b.addEventListener("click", () => setLang(b.dataset.lang));
}

document.addEventListener("langchange", () => {
  renderExamples();
  renderContracts();
  renderDiagrams();
  renderEval();
  // The model's explanations were written in the previous language; labels around them follow the switch.
  if (state.lastResult) renderResult(state.lastResult);
  if (!$("#submit").disabled) $("#submit").textContent = t("form.submit");
});

/* ---------------------------------------------------------------- boot */

applyStaticI18n();
renderExamples();
renderDiagrams();
loadContracts();
showTab(location.hash.slice(1) || "analyse");

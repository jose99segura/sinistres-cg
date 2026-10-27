"use strict";

const EXAMPLES = [
  ["Vélo volé, local commun ouvert", "Mon vélo a été volé dans le local commun de l'immeuble, qui n'était pas fermé à clé."],
  ["Bougie fondue sur la table de jardin", "Pendant mes vacances, une bougie laissée sur la table de mon jardin a fondu avec la chaleur et a abîmé la table."],
  ["Fuite de la machine à laver", "Le tuyau de ma machine à laver a lâché et l'eau a abîmé le parquet du salon."],
  ["Ordinateur portable tombé", "J'ai fait tomber mon ordinateur portable par terre chez moi, l'écran est cassé."],
  ["Cave inondée par un orage", "Après un violent orage, l'eau de pluie est entrée dans ma cave et a abîmé les cartons qui y étaient stockés."],
  ["Bijoux volés, porte forcée", "Des cambrioleurs ont forcé la porte d'entrée de ma maison et ont volé mes bijoux pendant que j'étais au travail."],
];

const ROLE_LABELS = { garantie: "Garantie", exclusion: "Exclusion", condition: "Condition", definition: "Définition", limite: "Limite" };
const VERDICT_LABELS = { couvert: "Couvert", non_couvert: "Non couvert", indetermine: "Indéterminé" };
const VERDICT_ICONS = { couvert: "✓", non_couvert: "✕", indetermine: "?" };

const $ = (sel) => document.querySelector(sel);
let state = { contracts: [], perils: {}, contractId: null };

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

/* ---------------------------------------------------------------- tabs */

function showTab(name) {
  for (const t of document.querySelectorAll(".tab")) t.classList.toggle("active", t.dataset.tab === name);
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
    $("#contracts").innerHTML = `<p class="error">Les contrats ne se chargent pas. Rechargez la page dans un instant.</p>`;
    return;
  }
  state.contracts = data.contracts;
  state.perils = data.perils;
  const box = $("#contracts");
  box.innerHTML = data.contracts.map((c, i) => `
    <label class="contract${i === 0 ? " selected" : ""}">
      <input type="radio" name="contract" value="${esc(c.id)}" ${i === 0 ? "checked" : ""}>
      <span class="name">${esc(c.insurer)} — ${esc(c.product)}</span>
      <span class="meta">Version ${esc(c.version)} · ${c.n_pages} pages · ${c.n_clauses} clauses ·
        <a href="${esc(c.url)}" target="_blank" rel="noopener">PDF source</a></span>
    </label>`).join("");
  state.contractId = data.contracts[0]?.id;
  box.addEventListener("change", (e) => {
    state.contractId = e.target.value;
    for (const l of box.querySelectorAll(".contract")) l.classList.toggle("selected", l.querySelector("input").checked);
  });
}

function renderExamples() {
  $("#examples").innerHTML = EXAMPLES.map(([label], i) => `<button type="button" class="chip" data-i="${i}">${esc(label)}</button>`).join("");
  $("#examples").addEventListener("click", (e) => {
    const b = e.target.closest(".chip");
    if (!b) return;
    $("#claim").value = EXAMPLES[b.dataset.i][1];
    $("#claim").focus();
  });
}

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
  return out + esc(text.slice(pos));
}

/* ---------------------------------------------------------------- result */

function renderResult(r) {
  const v = r.verdict;
  const downgraded = r.verdict !== r.verdict_modele;
  const missing = r.informations_manquantes || [];
  const options = r.garanties_a_verifier || [];

  const steps = r.etapes.map((s, i) => {
    const c = s.clause;
    const pages = c.page_start === c.page_end ? `p. ${c.page_start}` : `p. ${c.page_start}–${c.page_end}`;
    return `
      <div class="card cite">
        <div class="cite-head">
          <span class="role ${esc(s.role)}">${esc(ROLE_LABELS[s.role] || s.role)}</span>
          <span class="where">${pages} · ${esc(c.section_path || "—")}</span>
          ${s.verifiee
            ? `<span class="check ok" title="Citation retrouvée mot pour mot dans le texte du contrat">✓ citation vérifiée</span>`
            : `<span class="check ko" title="Ces mots n'ont pas été retrouvés dans la clause : l'étape n'est pas prise en compte">⚠ citation introuvable</span>`}
        </div>
        <p class="explication">${esc(s.explication)}</p>
        <div class="clause-text${s.verifiee ? "" : " unverified"}">${s.verifiee ? markCitation(c.text, s.citation) : esc(c.text)}</div>
        ${s.verifiee ? "" : `<p class="small muted">Citation proposée par le modèle : « ${esc(s.citation)} »</p>`}
        <div class="cite-actions">
          <button type="button" class="link-btn" data-page="${c.page_start}" data-lines="${(s.lignes || []).join(",")}"
            data-title="${esc(`${r.contract.insurer} — ${pages} — ${c.section_path}`)}">Voir dans le PDF</button>
        </div>
      </div>`;
  }).join("");

  const perils = (r.analyse_sinistre.perils || []).map((p) => `<span class="tag">${esc(state.perils[p] || p)}</span>`).join("");
  const termes = (r.analyse_sinistre.termes || []).map((t) => `<span class="tag">${esc(t)}</span>`).join("");

  $("#result").innerHTML = `
    <div class="card verdict ${v}">
      <div class="verdict-head">
        <span class="badge ${v}">${VERDICT_ICONS[v]} ${VERDICT_LABELS[v]}</span>
        <span class="contract-name">${esc(r.contract.insurer)} — ${esc(r.contract.product)} (${esc(r.contract.version)})</span>
      </div>
      <p class="resume">${esc(r.resume)}</p>
      ${r.constats ? `<div class="constats">
        ${[["garantie", "Une garantie s'applique"], ["exclusion", "Une exclusion s'applique"], ["condition_non_remplie", "Une condition n'est pas remplie"]]
          .map(([k, l]) => `<span class="constat ${r.constats[k]}">${l}&nbsp;: <b>${{ oui: "oui", non: "non", incertain: "incertain" }[r.constats[k]]}</b></span>`).join("")}
      </div>` : ""}
      ${r.qualification ? `<p class="qualif"><b>Qualification des faits&nbsp;:</b> ${esc(r.qualification)}</p>` : ""}
      ${downgraded ? `<p class="downgraded">Le modèle proposait « ${VERDICT_LABELS[r.verdict_modele]} », mais ce verdict ne reposait pas sur une clause vérifiée : il a été rétrogradé.</p>` : ""}
    </div>

    <div class="boxes">
      <div class="card box ${missing.length ? "" : "empty"}">
        <h3>Ce qui déciderait</h3>
        ${missing.length ? `<ul>${missing.map((m) => `<li>${esc(m)}</li>`).join("")}</ul>` : "Aucun fait manquant signalé."}
      </div>
      <div class="card box ${options.length ? "" : "empty"}">
        <h3>À vérifier dans vos Conditions Particulières</h3>
        ${options.length ? `<ul>${options.map((m) => `<li>${esc(m)}</li>`).join("")}</ul>` : "Aucune garantie optionnelle en jeu."}
      </div>
    </div>

    <h3 class="section-title">Clauses sur lesquelles repose la réponse (${r.etapes.length})</h3>
    ${steps || `<div class="card box empty">Aucune clause citée.</div>`}

    <details class="card trace">
      <summary>Comment la réponse a été construite</summary>
      <dl class="kv">
        <dt>Périls détectés</dt><dd>${perils}</dd>
        <dt>Termes recherchés</dt><dd>${termes}</dd>
        <dt>Clauses lues</dt><dd>${r.clauses_lues.lues} sur ${r.clauses_lues.total} clauses du contrat</dd>
        <dt>Contrôles</dt><dd>${(r.controles || []).map((c) => esc(c)).join("<br>") || "—"}</dd>
        <dt>Modèle</dt><dd>${esc(r.modele)} · ${r.duree_s} s</dd>
      </dl>
    </details>`;
}

/* ---------------------------------------------------------------- PDF page dialog */

function openPage(btn) {
  const dlg = $("#page-dialog");
  $("#page-title").textContent = btn.dataset.title;
  const img = $("#page-img");
  img.src = `/api/page/${encodeURIComponent(state.lastContract)}/${btn.dataset.page}.png?lines=${btn.dataset.lines}`;
  dlg.showModal();
  img.onload = () => {
    // Scroll to the highlighted lines is approximate: start near the top of the cited passage.
    dlg.querySelector(".dialog-body").scrollTop = 0;
  };
}

$("#page-close").addEventListener("click", () => $("#page-dialog").close());
$("#page-dialog").addEventListener("click", (e) => { if (e.target.id === "page-dialog") e.target.close(); });
$("#result").addEventListener("click", (e) => {
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
    err.textContent = "Décrivez le sinistre en une ou deux phrases (au moins 15 caractères).";
    err.hidden = false;
    return;
  }
  const btn = $("#submit");
  btn.disabled = true;
  btn.textContent = "Analyse en cours…";
  $("#result").innerHTML = $("#tpl-loading").innerHTML;
  try {
    const r = await fetch("/api/analyse", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ contract_id: state.contractId, claim }),
    });
    const data = await r.json();
    if (!r.ok) throw new Error(typeof data.detail === "string" ? data.detail : "La requête a échoué.");
    state.lastContract = data.contract.id;
    renderResult(data);
    if (window.innerWidth < 900) $("#result").scrollIntoView({ behavior: "smooth" });
  } catch (ex) {
    $("#result").innerHTML = `<div class="card placeholder"><p class="ph-title">Pas de réponse</p><p class="error">${esc(ex.message)}</p></div>`;
  } finally {
    btn.disabled = false;
    btn.textContent = "Analyser le sinistre";
  }
});

/* ---------------------------------------------------------------- evaluation tab */

let evalLoaded = false;
async function loadEval() {
  if (evalLoaded) return;
  evalLoaded = true;
  const r = await (await fetch("/api/eval")).json();
  if (r.available === false) {
    $("#eval").innerHTML = "<p class='muted'>Le rapport d'évaluation n'est pas encore disponible.</p>";
    return;
  }
  const m = r.metrics;
  const pct = (x) => (x == null ? "—" : `${Math.round(x * 100)} %`);
  const rows = r.cases.map((c) => `
    <tr>
      <td>${esc(c.id)}</td>
      <td>${esc(c.contract)}</td>
      <td>${esc(c.claim)}</td>
      <td>${VERDICT_LABELS[c.expected]}</td>
      <td class="${c.verdict_ok ? "ok-txt" : "ko-txt"}">${VERDICT_LABELS[c.got] || esc(c.got)}</td>
      <td>${c.expected_clause_hit == null ? "—" : c.expected_clause_hit ? "✓" : "✕"}</td>
      <td>${c.citations_verified}/${c.citations_total}</td>
    </tr>`).join("");
  $("#eval").innerHTML = `
    <h2>Évaluation</h2>
    <p>${r.cases.length} sinistres annotés à la main sur les trois contrats, avec le verdict attendu et la clause qui doit être citée.
      Lancé le ${esc(r.run_at)} avec <code>${esc(r.model)}</code>. Commande&nbsp;: <code>uv run sinistres eval</code>.</p>
    <div class="metrics">
      <div class="metric"><div class="v">${pct(m.verdict_accuracy)}</div><div class="l">Verdicts corrects</div></div>
      <div class="metric"><div class="v">${pct(m.expected_clause_recall)}</div><div class="l">Clause attendue citée</div></div>
      <div class="metric"><div class="v">${pct(m.citation_verified_rate)}</div><div class="l">Citations retrouvées mot pour mot</div></div>
      <div class="metric"><div class="v">${pct(m.abstention_recall)}</div><div class="l">« Indéterminé » quand il le fallait</div></div>
      <div class="metric"><div class="v">${pct(m.wrong_confident_rate)}</div><div class="l">Verdicts assurés et faux</div></div>
    </div>
    <div class="table-scroll"><table>
      <thead><tr><th>Cas</th><th>Contrat</th><th>Sinistre</th><th>Attendu</th><th>Obtenu</th><th>Clause</th><th>Citations</th></tr></thead>
      <tbody>${rows}</tbody>
    </table></div>
    <p class="muted small">Les verdicts attendus supposent la garantie optionnelle concernée souscrite, comme le système. Un « indéterminé » sur un cas tranché compte comme une erreur, mais pas comme une erreur assurée.</p>`;
}

/* ---------------------------------------------------------------- boot */

renderExamples();
loadContracts();
showTab(location.hash.slice(1) || "analyse");

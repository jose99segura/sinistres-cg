"""Turn numbered lines into a section outline and clauses, then label each clause.

Two model passes, both returning line numbers or labels only, never text:

1. Structure, one call per page (parallel): which lines are headings, and where each clause
   starts and ends. A clause may run onto the next page, so the model also sees the head of it.
2. Meaning, one call per batch of clauses: kind (guarantee, exclusion...), perils, defined term.
   Done after the outline is known, so each clause is labelled with its full section path
   ("6. Garanties optionnelles > a. Vol / Vandalisme > Sont exclus :").

The result is cached as JSON in data/segments/ and committed: the deployed build re-creates the
database from the PDFs and these line numbers without calling a model.
"""

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pydantic import BaseModel, Field

from .. import config, llm
from ..taxonomy import Kind, Peril
from .pdf import Line

# ---------------------------------------------------------------- pass 1: structure


class Heading(BaseModel):
    line: int
    end: int = Field(description="last line of the heading; same as line when it fits on one line")
    level: int = Field(description="1 = chapter, 2 = section, 3 = subsection, 4 = sub-subsection, 5 = list lead-in")


class Span(BaseModel):
    start: int
    end: int


class PageStructure(BaseModel):
    headings: list[Heading]
    clauses: list[Span]


STRUCTURE_SYSTEM = """You segment pages of a French home-insurance contract (conditions générales).
You receive numbered lines. Lines marked [B] are bold, (size) is the font size.

Return:
- headings: lines that are titles of chapters/sections/subsections, with a level (1 = chapter, 2 = section,
  3 = subsection, 4 = deeper). Use numbering (1., 1.1, a., Article 3) and typography to choose the level.
  A short lead-in sentence that introduces a list ("Sont exclus :", "Nous garantissons :", "Ne sont pas
  assurés, les dommages causés :") is a heading of level 5. A heading may span two lines: line = first, end = last.
- clauses: contiguous line ranges [start, end] of body text, in order. A clause is the smallest unit that
  can be cited on its own: one definition, one item of a numbered or bulleted list, or one paragraph.
  Keep a sentence that continues on the next lines in the same clause.

Rules:
- Only return clauses that START on the CURRENT page. A clause may END on a line of the NEXT page
  (shown for reference) when its sentence continues there.
- Do not return heading lines inside clauses.
- Skip tables of contents, page furniture and lines with no contract content.
- Line numbers must be ones that appear in the input."""


def _fmt(lines: list[Line]) -> str:
    return "\n".join(f"{l.n} {'[B] ' if l.bold else ''}({l.size}) {l.text}" for l in lines)


def page_structure(page_lines: list[Line], prev_tail: list[Line], next_head: list[Line]) -> PageStructure:
    user = (
        "PREVIOUS PAGE (end, context only):\n" + _fmt(prev_tail)
        + "\n\nCURRENT PAGE:\n" + _fmt(page_lines)
        + "\n\nNEXT PAGE (start, only to finish a clause that continues):\n" + _fmt(next_head)
    )
    result = llm.structured(STRUCTURE_SYSTEM, user, PageStructure)

    # Keep only what is consistent with the rules; the model's output is checked, not trusted.
    first, last = page_lines[0].n, page_lines[-1].n
    limit = next_head[-1].n if next_head else last
    headings = [h for h in result.headings if first <= h.line <= last]
    for h in headings:
        h.end = h.end if h.line <= h.end <= min(h.line + 2, last) else h.line
    heading_lines = {n for h in headings for n in range(h.line, h.end + 1)}
    clauses = [
        c for c in result.clauses
        if first <= c.start <= last and c.start <= c.end <= limit and c.start not in heading_lines
    ]

    # Coverage guarantee: a body line the model skipped becomes a clause of its own (runs of
    # consecutive skipped lines are kept together). No contract text is silently dropped.
    covered = set(heading_lines) | {n for c in clauses for n in range(c.start, c.end + 1)}
    run: list[int] = []
    for l in page_lines + [None]:
        if l is not None and l.n not in covered and not l.text.endswith("…"):
            run.append(l.n)
            continue
        if run:
            clauses.append(Span(start=run[0], end=run[-1]))
            run = []
    clauses.sort(key=lambda c: c.start)
    return PageStructure(headings=headings, clauses=clauses)


# ---------------------------------------------------------------- pass 1b: one outline for the contract


class OutlineLevel(BaseModel):
    line: int
    level: int


class Outline(BaseModel):
    headings: list[OutlineLevel]


OUTLINE_SYSTEM = """You receive every heading found in a French insurance contract, in order, with its page,
font size, bold flag and a provisional level that was chosen page by page and is inconsistent.
Rebuild the table of contents: give every heading a level so that the hierarchy is consistent across the whole
document. 1 = chapter. Use the numbering first ("6." < "6.a" or "a." < "1.1.2"), then typography (bigger or bold =
higher). Sibling headings with the same numbering style must get the same level. Short lead-ins that introduce a
list ("Sont exclus :", "Nous garantissons :") stay one level below the heading they belong to.
Return one entry per input line number, in the same order."""


def normalize_outline(lines: list[Line], headings: list[dict]) -> list[dict]:
    """Make heading levels consistent across pages with one call over the whole heading list."""
    if not headings:
        return headings
    rows = []
    for h in headings:
        l = lines[h["line"]]
        title = " ".join(x.text for x in lines[h["line"]:h["end"] + 1])[:120]
        rows.append(f"{h['line']} | p{l.page} | size {l.size} | {'bold' if l.bold else 'regular'} | level {h['level']} | {title}")
    out: dict[int, int] = {}
    # Long outlines are sent in overlapping chunks; the overlap carries the hierarchy across.
    step, overlap = 160, 30
    for i in range(0, len(rows), step):
        chunk = rows[max(0, i - overlap):i + step]
        result = llm.structured(OUTLINE_SYSTEM, "\n".join(chunk), Outline)
        for h in result.headings:
            if 1 <= h.level <= 6:
                out[h.line] = h.level
    return [{**h, "level": out.get(h["line"], h["level"])} for h in headings]


# ---------------------------------------------------------------- pass 2: meaning


class ClauseLabel(BaseModel):
    id: int
    kind: Kind
    perils: list[Peril] = Field(description="every peril the clause is relevant to; 'general' if it applies to all")
    defined_term: str | None = Field(description="for a definition, the term defined, as written; else null")
    title: str = Field(description="short French label of what the clause says, max 10 words")


class Labels(BaseModel):
    labels: list[ClauseLabel]


LABEL_SYSTEM = """You label clauses of a French home-insurance contract (conditions générales).
For each clause you get an id, its section path and its text. Return one label per id:

- kind: definition | garantie (what is covered) | exclusion (what is not covered) |
  condition (a condition the cover depends on, or a prevention obligation such as locking doors) |
  limite (ceiling, deductible, valuation, indemnity rule) | procedure (what to do after a loss, deadlines,
  proof) | administratif (premium, duration, termination, law, complaints) | autre.
  An item under a lead-in like "Sont exclus" is an exclusion even if it does not repeat the word.
- perils: all that apply among general, incendie, degats_des_eaux, tempete_grele_neige,
  catastrophes_naturelles, vol_vandalisme, bris_de_glace, dommages_electriques, objets_valeur_tous_risques
  (valuables, multimedia, leisure items, bicycles, all-risk), jardin_exterieurs (garden, outdoor furniture,
  pool), responsabilite_civile, protection_juridique, assistance, pertes_indirectes.
  Use the section path: a clause under "Vol" is about vol_vandalisme. Use "general" for definitions of
  general terms, common exclusions and obligations that apply to every guarantee.
- defined_term: for a definition, the term it defines; otherwise null.
- title: a short French label."""


def label_clauses(batch: list[dict]) -> list[ClauseLabel]:
    user = "\n\n".join(f"id={c['id']}\nsection: {c['section_path']}\ntext: {c['text']}" for c in batch)
    result = llm.structured(LABEL_SYSTEM, user, Labels)
    by_id = {l.id: l for l in result.labels}
    missing = [c for c in batch if c["id"] not in by_id]
    if missing and len(batch) > 1:
        # A small model sometimes skips an item in a long batch: ask again for those alone.
        for c in missing:
            by_id[c["id"]] = label_clauses([c])[0]
    elif missing:
        c = missing[0]
        # Still nothing: keep the clause, with a neutral label, rather than lose the contract.
        by_id[c["id"]] = ClauseLabel(id=c["id"], kind="autre", perils=["general"], defined_term=None,
                                     title=c["text"][:60])
    return [by_id[c["id"]] for c in batch]


# ---------------------------------------------------------------- the whole contract


def lines_fingerprint(lines: list[Line]) -> str:
    return hashlib.sha256("\n".join(l.text for l in lines).encode()).hexdigest()[:16]


def section_paths(lines: list[Line], headings: list[dict]) -> dict[int, str]:
    """Section path in force at every line, from the flat list of headings."""
    by_line = {h["line"]: h for h in headings}
    stack: list[tuple[int, str]] = []
    paths: dict[int, str] = {}
    for l in lines:
        h = by_line.get(l.n)
        if h:
            title = " ".join(x.text for x in lines[h["line"]:h["end"] + 1])
            while stack and stack[-1][0] >= h["level"]:
                stack.pop()
            stack.append((h["level"], title))
        paths[l.n] = " > ".join(t for _, t in stack)
    return paths


def segment_contract(contract_id: str, lines: list[Line], workers: int = 6, log=print) -> dict:
    cache = config.SEGMENTS_DIR / f"{contract_id}.json"
    fingerprint = lines_fingerprint(lines)
    if cache.exists():
        data = json.loads(cache.read_text(encoding="utf-8"))
        if data["fingerprint"] == fingerprint:
            if not data.get("outline_normalized"):
                log(f"{contract_id}: normalising the outline")
                data["headings"] = normalize_outline(lines, data["headings"])
                data["outline_normalized"] = True
                cache.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
            return data
        log(f"{contract_id}: PDF text changed since the cached segmentation, segmenting again")

    pages = sorted({l.page for l in lines})
    by_page = {p: [l for l in lines if l.page == p] for p in pages}

    def one_page(i: int) -> PageStructure:
        p = pages[i]
        prev_tail = by_page[pages[i - 1]][-8:] if i > 0 else []
        next_head = by_page[pages[i + 1]][:12] if i + 1 < len(pages) else []
        return page_structure(by_page[p], prev_tail, next_head)

    # The structure pass is the expensive one: keep it on disk so a failure later does not redo it.
    partial = config.SEGMENTS_DIR / f"{contract_id}.structure.json"
    if partial.exists() and json.loads(partial.read_text(encoding="utf-8"))["fingerprint"] == fingerprint:
        structures = [PageStructure.model_validate(s)
                      for s in json.loads(partial.read_text(encoding="utf-8"))["pages"]]
    else:
        log(f"{contract_id}: structure of {len(pages)} pages")
        with ThreadPoolExecutor(workers) as pool:
            structures = list(pool.map(one_page, range(len(pages))))
        partial.parent.mkdir(parents=True, exist_ok=True)
        partial.write_text(json.dumps({"fingerprint": fingerprint, "pages": [s.model_dump() for s in structures]}),
                           encoding="utf-8")

    headings = [{"line": h.line, "end": h.end, "level": h.level} for s in structures for h in s.headings]
    spans = sorted({(c.start, c.end) for s in structures for c in s.clauses})
    # Overlapping spans: the earlier one stops where the next one starts.
    clean: list[tuple[int, int]] = []
    for start, end in spans:
        if clean and start <= clean[-1][1]:
            prev_start, _ = clean[-1]
            if start == prev_start:
                continue
            clean[-1] = (prev_start, start - 1)
        clean.append((start, end))

    log(f"{contract_id}: normalising the outline")
    headings = normalize_outline(lines, headings)
    paths = section_paths(lines, headings)
    heading_lines = {n for h in headings for n in range(h["line"], h["end"] + 1)}
    clauses = []
    for start, end in clean:
        text = " ".join(l.text for l in lines[start:end + 1] if l.n not in heading_lines)
        clauses.append({"id": len(clauses), "start": start, "end": end, "section_path": paths[start], "text": text})

    log(f"{contract_id}: labelling {len(clauses)} clauses")
    batches = [clauses[i:i + 25] for i in range(0, len(clauses), 25)]
    with ThreadPoolExecutor(workers) as pool:
        labelled = [l for ls in pool.map(label_clauses, batches) for l in ls]
    for c, label in zip(clauses, labelled):
        c.update(kind=label.kind, perils=sorted(set(label.perils)), defined_term=label.defined_term, title=label.title)

    data = {
        "contract_id": contract_id,
        "fingerprint": fingerprint,
        "model": config.MISTRAL_MODEL,
        "headings": headings,
        "outline_normalized": True,
        # Text is not stored: it is re-read from the PDF at build time.
        "clauses": [{k: v for k, v in c.items() if k not in ("text", "section_path")} for c in clauses],
    }
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return data


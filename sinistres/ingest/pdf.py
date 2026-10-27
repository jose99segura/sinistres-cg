"""PDF -> numbered lines in reading order, with page and position.

Everything downstream points at these lines, so the text of a clause is always the PDF's own text,
never a model's rewrite of it.
"""

import re
from collections import Counter
from dataclasses import dataclass

import pymupdf


@dataclass
class Line:
    n: int  # global line number inside the contract, 0-based
    page: int  # 1-based PDF page
    text: str
    bold: bool
    size: float
    bbox: tuple[float, float, float, float]


BULLETS = {"◼", "■", "▪", "•", "●", "✓", "✔", "–", "-", "l"}


def _norm_repeat(text: str) -> str:
    # Running headers/footers differ only by the page number ("PAGE 33/100", "15 | 48").
    return re.sub(r"\d+", "#", text.strip().lower())


def _line_dict(ln) -> dict | None:
    if abs(ln["dir"][1]) > 0.1:  # vertical margin text
        return None
    spans = [s for s in ln["spans"] if s["text"].strip()]
    if not spans:
        return None
    text = re.sub(r"\s+", " ", "".join(s["text"] for s in ln["spans"])).strip()
    # Table-of-contents leader dots carry no content.
    text = re.sub(r"(\s?\.){4,}", " …", text)
    if len(text) <= 1 or text in BULLETS:  # bullet glyphs drawn as their own line
        return None
    chars = sum(len(s["text"]) for s in spans)
    bold_chars = sum(len(s["text"]) for s in spans if s["flags"] & 16 or "Bold" in s["font"])
    return {
        "text": text,
        "bold": bold_chars > 0.6 * chars,
        "size": round(max(s["size"] for s in spans), 1),
        "bbox": tuple(round(v, 1) for v in ln["bbox"]),
    }


def _merge(a: dict, b: dict) -> dict:
    """Join two fragments of one visual line (e.g. an article number and its text)."""
    return {
        "text": f"{a['text']} {b['text']}",
        "bold": a["bold"] and b["bold"],
        "size": max(a["size"], b["size"]),
        "bbox": (min(a["bbox"][0], b["bbox"][0]), min(a["bbox"][1], b["bbox"][1]),
                 max(a["bbox"][2], b["bbox"][2]), max(a["bbox"][3], b["bbox"][3])),
    }


def _page_lines(page: pymupdf.Page) -> list[dict]:
    """Lines of one page in reading order, handling two-column layouts."""
    mid = page.rect.width / 2
    blocks = [b for b in page.get_text("dict")["blocks"] if b.get("type") == 0]

    def column(b) -> str:
        x0, _, x1, _ = b["bbox"]
        if x1 <= mid + 10:
            return "L"
        if x0 >= mid - 10:
            return "R"
        return "F"  # full width

    chars = Counter()
    for b in blocks:
        chars[column(b)] += sum(len(s["text"]) for ln in b["lines"] for s in ln["spans"])
    total = sum(chars.values()) or 1
    two_columns = chars["L"] > 0.25 * total and chars["R"] > 0.25 * total

    if two_columns:
        # Full-width blocks cut the page into bands; inside a band, read the left column
        # top to bottom, then the right one.
        blocks.sort(key=lambda b: b["bbox"][1])
        ordered, band = [], []
        for b in blocks:
            if column(b) == "F":
                ordered += sorted(band, key=lambda b: (column(b), b["bbox"][1]))
                ordered.append(b)
                band = []
            else:
                band.append(b)
        ordered += sorted(band, key=lambda b: (column(b), b["bbox"][1]))
        return [d for b in ordered for ln in b["lines"] if (d := _line_dict(ln))]

    # Single column: sort lines top to bottom and join fragments that share a baseline,
    # such as a numbering column ("3.1.4.2.1.") and the text next to it.
    lines = sorted((d for b in blocks for ln in b["lines"] if (d := _line_dict(ln))),
                   key=lambda d: (d["bbox"][1], d["bbox"][0]))
    out: list[dict] = []
    for d in lines:
        if out:
            prev = out[-1]
            same_row = abs((prev["bbox"][1] + prev["bbox"][3]) / 2 - (d["bbox"][1] + d["bbox"][3]) / 2) < 3
            if same_row and d["bbox"][0] >= prev["bbox"][2] - 2:
                out[-1] = _merge(prev, d)
                continue
        out.append(d)
    return out


def extract_lines(path: str, page_ranges: list[list[int]] | None = None) -> list[Line]:
    doc = pymupdf.open(path)
    if page_ranges:
        pages = [p for a, b in page_ranges for p in range(a, b + 1)]
    else:
        pages = list(range(1, doc.page_count + 1))

    raw = {p: _page_lines(doc[p - 1]) for p in pages}

    # A line that repeats on a third of the pages is a running header or footer.
    counts = Counter(_norm_repeat(l["text"]) for ls in raw.values() for l in {_norm_repeat(x["text"]): x for x in ls}.values())
    threshold = max(3, len(pages) // 3)
    repeated = {k for k, c in counts.items() if c >= threshold}

    lines: list[Line] = []
    for p in pages:
        for l in raw[p]:
            key = _norm_repeat(l["text"])
            if (key in repeated and len(re.findall(r"[a-zà-ÿ]", key)) >= 3) or re.fullmatch(r"[\d\s|/]+", l["text"]):
                continue
            lines.append(Line(len(lines), p, l["text"], l["bold"], l["size"], l["bbox"]))
    return lines

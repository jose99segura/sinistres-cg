"""Build the database from contracts.yaml: download, verify, extract, segment, store.

Re-running is cheap: segmentation is cached per contract in data/segments/, keyed by a fingerprint
of the extracted text, so only a new or changed PDF costs model calls.
"""

import hashlib
import json

import httpx
import yaml

from .. import config, db, search
from .pdf import extract_lines
from .segment import section_paths, segment_contract


def load_registry() -> list[dict]:
    return yaml.safe_load(config.CONTRACTS_FILE.read_text(encoding="utf-8"))["contracts"]


def ensure_pdf(entry: dict, log=print):
    path = config.PDF_DIR / f"{entry['id']}.pdf"
    if not path.exists():
        log(f"{entry['id']}: downloading {entry['url']}")
        path.parent.mkdir(parents=True, exist_ok=True)
        r = httpx.get(entry["url"], follow_redirects=True, timeout=60,
                      headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                             "(KHTML, like Gecko) Chrome/130.0 Safari/537.36",
                               "Accept": "application/pdf,*/*"})
        r.raise_for_status()
        path.write_bytes(r.content)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if entry.get("sha256") and digest != entry["sha256"]:
        # A different file means the line numbers in data/segments/ no longer point at the same text.
        raise RuntimeError(f"{entry['id']}: sha256 {digest} does not match contracts.yaml; the insurer changed the PDF")
    return path, digest


def build(only: list[str] | None = None, log=print) -> None:
    registry = [e for e in load_registry() if not only or e["id"] in only]
    tmp = config.DB_PATH.with_suffix(".tmp")
    tmp.unlink(missing_ok=True)
    conn = db.connect(tmp)

    for entry in registry:
        path, digest = ensure_pdf(entry, log)
        lines = extract_lines(str(path), entry.get("pages"))
        seg = segment_contract(entry["id"], lines, log=log)
        paths = section_paths(lines, seg["headings"])
        heading_lines = {n for h in seg["headings"] for n in range(h["line"], h["end"] + 1)}

        cid = entry["id"]
        conn.executemany(
            "insert into lines values (?,?,?,?,?,?,?,?)",
            [(cid, l.n, l.page, l.text, *l.bbox) for l in lines],
        )
        for c in seg["clauses"]:
            text = " ".join(l.text for l in lines[c["start"]:c["end"] + 1] if l.n not in heading_lines)
            if not text.strip():
                continue
            clause_id = f"{cid}:{c['id']:04d}"
            row = (clause_id, cid, c["id"], c["start"], c["end"], lines[c["start"]].page, lines[c["end"]].page,
                   paths[c["start"]], c["title"], c["kind"], c["defined_term"], text)
            conn.execute("insert into clauses values (?,?,?,?,?,?,?,?,?,?,?,?)", row)
            conn.executemany("insert into clause_perils values (?,?)", [(clause_id, p) for p in c["perils"]])
            stems = search.normalise(" ".join([text, c["title"], paths[c["start"]], c["defined_term"] or ""]))
            conn.execute("insert into clauses_fts values (?,?,?,?,?,?)",
                         (clause_id, text, c["title"], paths[c["start"]], c["defined_term"] or "", stems))

        n_clauses = conn.execute("select count(*) from clauses where contract_id = ?", (cid,)).fetchone()[0]
        conn.execute(
            "insert into contracts values (?,?,?,?,?,?,?,?,?,?,?)",
            (cid, entry.get("product_key", cid), entry["insurer"], entry["product"], entry["version"], entry["effective"], entry["url"], digest,
             len({l.page for l in lines}), n_clauses, seg["model"]),
        )
        conn.commit()
        log(f"{cid}: {len(lines)} lines, {n_clauses} clauses")

    conn.close()
    tmp.replace(config.DB_PATH)
    log(f"database written to {config.DB_PATH}")


def stats() -> str:
    conn = db.connect(readonly=True)
    rows = conn.execute(
        """select contract_id, kind, count(*) n from clauses group by contract_id, kind order by contract_id, n desc"""
    ).fetchall()
    return json.dumps([dict(r) for r in rows], ensure_ascii=False, indent=1)

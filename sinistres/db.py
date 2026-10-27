"""SQLite schema and queries.

One row per contract (the index), one row per PDF line (positions, for highlighting), one row per
clause with its section path, kind and perils. The perils sit in their own table so that "every
exclusion about theft, in every contract" is a plain join.
"""

import json
import sqlite3
from pathlib import Path

from . import config

SCHEMA = """
create table if not exists contracts (
    id text primary key,
    insurer text not null,
    product text not null,
    version text not null,
    effective text not null,
    url text not null,
    sha256 text not null,
    n_pages integer not null,
    n_clauses integer not null,
    model text not null
);
create table if not exists lines (
    contract_id text not null references contracts(id),
    n integer not null,
    page integer not null,
    text text not null,
    x0 real, y0 real, x1 real, y1 real,
    primary key (contract_id, n)
);
create table if not exists clauses (
    id text primary key,               -- "<contract>:<ord>"
    contract_id text not null references contracts(id),
    ord integer not null,
    start_n integer not null,
    end_n integer not null,
    page_start integer not null,
    page_end integer not null,
    section_path text not null,
    title text not null,
    kind text not null,
    defined_term text,
    text text not null
);
create index if not exists clauses_contract on clauses(contract_id, kind);
create table if not exists clause_perils (
    clause_id text not null references clauses(id),
    peril text not null,
    primary key (clause_id, peril)
);
create index if not exists clause_perils_peril on clause_perils(peril);
create virtual table if not exists clauses_fts using fts5(
    clause_id unindexed, text, title, section_path, defined_term,
    tokenize = 'unicode61 remove_diacritics 2'
);
"""


def connect(path: Path | None = None, readonly: bool = False) -> sqlite3.Connection:
    path = path or config.DB_PATH
    if readonly:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, check_same_thread=False)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(path)
        conn.executescript(SCHEMA)
    conn.row_factory = sqlite3.Row
    return conn


def contracts(conn) -> list[dict]:
    return [dict(r) for r in conn.execute("select * from contracts order by insurer")]


def clause_dicts(rows) -> list[dict]:
    out = []
    for r in rows:
        d = dict(r)
        if "perils" in d and isinstance(d["perils"], str):
            d["perils"] = json.loads(d["perils"])
        out.append(d)
    return out


CLAUSE_SELECT = """
select c.*, (select json_group_array(peril) from clause_perils p where p.clause_id = c.id) as perils
from clauses c
"""


def clauses_by_ids(conn, ids: list[str]) -> list[dict]:
    if not ids:
        return []
    marks = ",".join("?" * len(ids))
    rows = conn.execute(f"{CLAUSE_SELECT} where c.id in ({marks}) order by c.contract_id, c.ord", ids)
    return clause_dicts(rows)


def clause_lines(conn, clause_id: str) -> list[dict]:
    return [dict(r) for r in conn.execute(
        """select l.* from lines l join clauses c
           on l.contract_id = c.contract_id and l.n between c.start_n and c.end_n
           where c.id = ? order by l.n""", (clause_id,))]

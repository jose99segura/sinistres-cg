# Couvert ou pas ? — a claim against the general conditions, with its sources

**Live demo:** https://sinistres-cg-820639010070.europe-west1.run.app (cold start: the first request can take ~20 s)

**Code:** https://github.com/jose99segura/sinistres-cg

Describe a home-insurance claim in French. The app reads the insurer's *conditions générales* and answers
**couvert**, **non couvert** or **indéterminé**, says why, and shows the clauses it relies on: quoted word
for word, with page and section, highlighted on the PDF page. When the contract does not settle the case,
it says so and lists what would. The interface switches between French and English: the model then writes its
explanations in English, while citations stay word for word in the contract's French. The "How it's built"
tab explains the pipeline with five diagrams.

Built as a small, finished answer to topic 1 of the recruitment exercise "Un sinistre, et les conditions
générales". Personal project; the contracts are public PDFs downloaded from the insurers' websites, and the
app has no link with the insurers it cites. It is not legal advice.

| Contract | Pages ingested | Clauses |
|---|---|---|
| Baloise Luxembourg — HOME, CG-HOME(2)-LUFR-09-24 | 48 | 549 |
| AXA Assurances Luxembourg — OptiHome, March 2022 | 117 | 915 |
| La Luxembourgeoise (Lalux) — easyPROTECT, home chapters, 15.04.2022 | 61 of 127 | 765 |

## What it does instead of putting the PDF in a chatbot

Each contract is **prepared once** and then queried like a database.

```
PDF ──► lines ──► outline + clauses ──► labels ──► SQLite        (once per contract)
claim ──► facts ──► SQL retrieval ──► structured decision ──► checks ──► UI   (per question)
```

1. **Lines** (`ingest/pdf.py`). PyMuPDF extracts every line with its page and position. Two-column pages are
   read column by column, running headers and footers are dropped, and numbering columns are joined to their
   text. Every later step points at these line numbers.
2. **Clauses** (`ingest/segment.py`). The model reads one page at a time (in parallel) and returns *line
   numbers only*: which lines are headings, and where each clause starts and ends. It never rewrites the
   text, so a clause's text is always the contract's own words. Any body line the model skips becomes a
   clause on its own: nothing is silently dropped. A second call over the whole list of headings rebuilds a
   consistent table of contents, so each clause gets a section path ("6. Garanties optionnelles › a. Vol ›
   Sont exclus").
3. **Labels.** Each clause gets a kind (garantie, exclusion, condition, définition, limite, procédure…) and
   perils from a **shared vocabulary** (`taxonomy.py`): vol, dégâts des eaux, incendie, jardin, objets de
   valeur/vélos… Every insurer names and orders chapters differently; the shared labels are what make one
   query work across all of them.
4. **Storage** (`db.py`). One row per contract (insurer, product, version, effective date, source URL,
   sha256), one per line (with its position, for highlighting), one per clause, a clause↔peril table and an
   FTS5 index. The segmentation is committed in `data/segments/` as line numbers and labels, without the
   contract text: the deployed image re-downloads the PDFs, checks their hash and rebuilds the database
   with no model call.
5. **Retrieval** (`answer/retrieve.py`). A first call turns the claim into facts (perils, property, place,
   words a contract would use). Then SQL, not a vector store: full-text search (BM25) on those words, every
   guarantee/exclusion/condition/limit labelled with the claim's perils, the exclusions that apply to every
   guarantee, and the definitions of the terms that appear. Typically 60–80 clauses out of 500–900.
   The full-text index holds a normalised copy of each clause (accents, plurals) and the claim's words are
   expanded with a hand-written insurance synonym table (`search.py`): "vélo" finds "cycle" and "objet de
   mobilité durable". No embeddings: in a contract the exact words decide ("fermé à clé", "sauf si"), and
   every retrieved clause keeps a readable reason (word, peril, general exclusion, definition).
6. **Findings, not a verdict** (`answer/analyse.py`). One structured-output call. The model qualifies the
   facts in the contract's words, cites the clauses, and then reports three findings, each `oui` / `non` /
   `incertain`: does a guarantee apply, does an exclusion apply, is a condition not met. The schema puts the
   citations *before* the findings, so the model reasons before it concludes. If the useful guarantee is
   optional, it assumes it subscribed and says so ("à vérifier dans vos Conditions Particulières").
   **A cascade:** the free small model (`ministral-14b`) answers first; a stronger one (`gemini-3.8-flash`)
   takes the decision over when the checks fail, when the answer is "indéterminé", and for every denial
   (models deny too readily). A denial is then reviewed separately: does the deciding clause really apply to
   the facts told, and does it contain an exception ("sauf", "toutefois")?
7. **Checks and the verdict, in code.**
   - Every citation must be found word for word in the clause it names (after normalising quotes, spaces,
     hyphens and markdown). If the words sit in exactly one other retrieved clause, the citation is moved
     there and the UI says so; otherwise it is shown as not found and ignored.
   - An exclusion or an unmet condition must rest on **words copied from the claim**, which are checked too.
     Without them the presumption holds (the policyholder met their obligations): a small model otherwise
     turns every claim into "it depends whether you maintained your washing machine".
   - The verdict is a rule: `non couvert` if no guarantee applies or an exclusion/unmet condition does;
     `couvert` if a guarantee applies and nothing takes it away; otherwise `indéterminé`.
   - `couvert` without a verified guarantee, or `non couvert` without the deciding clause verified, is
     **downgraded to "indéterminé"** and the UI says why. A sourced "je ne sais pas" beats a confident
     unsupported answer, and it shows what was examined (how many clauses, found how, which terms).

## Hundreds of contracts

- **Cost is paid per contract, once.** Ingesting a 100-page contract takes a few minutes and about 150 small
  model calls; answering a question costs two to four calls whatever the contract's size.
- **The contract is a row, the clause is a row.** Choosing which contract applies (insurer, product, version
  in force at the date of loss) is a filter on the `contracts` table, not a search. With the shared labels,
  questions across the portfolio are queries: *which contracts exclude bikes left in a shared room*, *which
  ones cover "dommages ménagers" without flames* — a `join` between `clauses` and `clause_perils`, then a
  read of a handful of rows.
- **The edition in force on the date of loss.** Each contract carries a `product_key` and an effective
  date; `db.contract_in_force(product_key, date)` picks the edition that applied when the loss happened.
- **Versions and changes are detected.** Each PDF is pinned by sha256; if an insurer replaces the file, the
  build stops instead of pointing old line numbers at new text.
- **What would change at scale:** Postgres instead of SQLite (same schema), a human review queue for clauses
  whose label confidence is low, and a curated vocabulary of perils and defined terms maintained with
  claims handlers rather than inferred from the documents.

## Evaluation

`eval/cases.yaml` holds 42 claims labelled by hand from the contracts, each with the page of the expected
answer: the expected verdict, the verdicts that are also defensible when the text is genuinely open (is a
room that is shut but not locked a "local non clos"?), and the clause the answer must cite. Cases are sliced
by what makes them hard — a plain guarantee, an exclusion, an exception inside an exclusion ("sauf si…"),
an unmet condition, a genuinely ambiguous case — and many come as **twins**: the same claim with one fact
changed, which must flip the verdict (a bike locked to a rack vs. left without a lock; a pipe embedded in
the wall vs. an exposed hose). One case is written in English.

```bash
uv run sinistres eval                 # the deployed cascade
uv run sinistres eval --mode cheap    # the small model alone
uv run sinistres eval --mode long     # no retrieval: the whole contract to the strong model
```

Same 42 cases, three designs (95% Wilson intervals in brackets):

| | Small model only | Cascade (deployed) |
|---|---|---|
| Verdict acceptable | 67 % (52–79) | **90 % (78–96)** |
| Expected clause cited | 74 % | **93 %** |
| Citations found word for word | 70 % | **93 %** |
| Says "indéterminé" when it should | 43 % | 71 % |
| When it says "indéterminé", it is right | 21 % | **100 %** |
| Confident and wrong | 12 % (5–25) | 10 % (4–22) |
| Escalated to the stronger model | — | 74 % |
| Mean time per claim | 22 s | 40 s |

The third design (no retrieval, the whole contract to `gemini-3.8-flash`) is being measured on the same cases; its result goes in `eval/results/long.md`.

By slice, for the cascade: guarantees 14/14, exclusions 11/12, ambiguous 6/7, exceptions 3/4, unmet
conditions 2/3, language 1/1. The full per-case table is in `eval/results/cascade.md` and in the app's
Evaluation tab.

What the numbers say, honestly:

- **The grounding is the strong part.** Nine answers in ten rest on the clause a human marked as decisive,
  and the quotes that cannot be found are shown as such, never silently used.
- **The cascade is what makes the verdicts usable**, and it is not free: three questions in four reach the
  stronger model, mostly because the small model answers "indéterminé" or denies. Tuning that threshold is
  the obvious next cost lever.
- **Confident errors did not disappear** (about one in ten). They sit where the literature says they do —
  conditions and exceptions — which is why denials and undetermined answers should go to a person
  (see Next steps).
- **The labels are mine.** 42 cases written by one person from the contracts are a smoke test, not a
  benchmark; the intervals are wide and results move a little between runs.

Earlier iterations (18 cases, small model only) are kept in `eval/results/run1.md`–`run3.md`: they are
how the design got here (model writes the verdict → model reports findings and code decides → doubts must
rest on the claim's words).

## Next steps (without over-engineering)

1. **Trace every answer in Langfuse** (prompt, retrieved clauses, findings, checks, model, cost) to review
   real cases, find the failure patterns, and turn reviewed cases into new evaluation cases.
2. **Hand doubts to a person.** "Indéterminé" and every denial go to a claims handler's queue with the
   cited clauses and the open questions already prepared; the system drafts, a human decides.
3. **Tune the cascade** on the traces: escalate less when the small model's answer is verified and
   consistent, keep every denial on the stronger model.
4. **Measure retrieval on its own** (is the gold clause among the 60–80 sent?) before adding anything; only
   if it misses, add embeddings as a fallback, not as the main path.
5. **Link the Conditions Particulières** when available: the options actually subscribed turn many
   "à vérifier" into a definite answer.

## Limits

- **The general conditions are not the contract.** Options, ceilings and deductibles live in the
  *Conditions Particulières*, which are not public. The app assumes the relevant option is subscribed and
  says which one to check.
- **Segmentation by a small model.** Contracts were split by `ministral-14b` (free Mistral tier):
  sometimes too coarse, with some wrong labels and section paths. Retrieval through several paths and the
  checks limit the effect.
- **Reasoning errors remain.** Even with the cascade, about one answer in ten is confidently wrong, mostly on
  conditions and exceptions: a verified quote can still be applied to the wrong situation. Hence the
  human queue in Next steps.
- **Tables and scanned PDFs** are not handled specially; Lalux's motor, travel and accident chapters are
  left out on purpose (`pages` in `contracts.yaml`).
- **Rate limits.** The public demo allows 20 analyses per IP per hour.

## Run it

```bash
cp .env.example .env            # add MISTRAL_API_KEY
uv sync
uv run sinistres build          # downloads the PDFs; segments only contracts not cached in data/segments/
uv run sinistres ask baloise-home-2024 "Mon vélo a été volé dans le local commun de l'immeuble, qui n'était pas fermé à clé."
uv run sinistres serve          # http://localhost:8080
```

Add a contract: one entry in `contracts.yaml` (URL, sha256, optional page ranges), then `uv run sinistres build`.

Deployed on Google Cloud Run (`deploy.sh`), key in Secret Manager.

### Python notes

- **Pydantic models are the contract with the model.** `llm.structured(system, user, Schema)` sends the
  JSON schema of `Schema` as Mistral's `response_format` and validates the answer again with Pydantic: a
  malformed answer is an error and is retried, never patched.
- **Threads, not asyncio.** Ingestion is I/O-bound and runs a `ThreadPoolExecutor`; a shared throttle in
  `llm.py` keeps all threads under the API's rate limit.
- **No framework for RAG.** Retrieval is three SQL queries; the whole answering path is
  `answer/retrieve.py` + `answer/analyse.py`, about 300 lines.

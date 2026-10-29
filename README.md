# Couvert ou pas ? — a claim against the general conditions, with its sources

**Live demo:** LIVE_URL

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
6. **Findings, not a verdict** (`answer/analyse.py`). One structured-output call. The model qualifies the
   facts in the contract's words, cites the clauses, and then reports three findings, each `oui` / `non` /
   `incertain`: does a guarantee apply, does an exclusion apply, is a condition not met. The schema puts the
   citations *before* the findings, so the model reasons before it concludes. If the useful guarantee is
   optional, it assumes it subscribed and says so ("à vérifier dans vos Conditions Particulières").
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
     unsupported answer.

## Hundreds of contracts

- **Cost is paid per contract, once.** Ingesting a 100-page contract takes a few minutes and about 150 small
  model calls; answering a question costs two calls whatever the contract's size.
- **The contract is a row, the clause is a row.** Choosing which contract applies (insurer, product, version
  in force at the date of loss) is a filter on the `contracts` table, not a search. With the shared labels,
  questions across the portfolio are queries: *which contracts exclude bikes left in a shared room*, *which
  ones cover "dommages ménagers" without flames* — a `join` between `clauses` and `clause_perils`, then a
  read of a handful of rows.
- **Versions and changes are detected.** Each PDF is pinned by sha256; if an insurer replaces the file, the
  build stops instead of pointing old line numbers at new text.
- **What would change at scale:** Postgres instead of SQLite (same schema), a human review queue for clauses
  whose label confidence is low, and a curated vocabulary of perils and defined terms maintained with
  claims handlers rather than inferred from the documents.

## Evaluation

`eval/cases.yaml` holds 18 claims labelled by hand from the contracts (page references in each case): the
expected verdict, the verdicts that are also defensible when the text is genuinely open (e.g. is a room
that is shut but not locked a "local non clos"?), and the clause the answer must cite. Several cases are
built so that the right answer is "indéterminé".

```bash
uv run sinistres eval
```

Latest run (2026-10-27 14:02, `ministral-14b-latest`):

| Metric | Value |
|---|---|
| Cases | 18 (0 errors) |
| Verdict acceptable | 61 % |
| Verdict equal to the expected one | 44 % |
| Expected clause cited | 83 % |
| Citations found word for word | 76 % |
| Abstention recall (said "indéterminé" when it should) | 29 % |
| Abstention precision | 29 % |
| Confident and wrong | 11 % |
| Verdicts downgraded by the checks | 1 |

| Case | Contract | Expected | Got | Expected clause cited | Citations verified |
|---|---|---|---|---|---|
| bal-velo-local-commun | baloise-home-2024 | indéterminé | ✓ non couvert | ✓ | 4/4 |
| bal-bougie-jardin | baloise-home-2024 | indéterminé | ✗ couvert | ✓ | 4/4 |
| bal-machine-a-laver | baloise-home-2024 | couvert | ✓ couvert | ✓ | 3/5 |
| bal-portable-tombe | baloise-home-2024 | couvert | ✗ indéterminé | ✗ | 1/4 |
| bal-bijoux-effraction | baloise-home-2024 | couvert | ✗ indéterminé | ✓ | 6/6 |
| bal-cle-paillasson | baloise-home-2024 | non couvert | ✓ non couvert | ✓ | 4/4 |
| bal-store-vent | baloise-home-2024 | indéterminé | ✓ indéterminé | ✓ | 2/4 |
| axa-velo-local-commun | axa-optihome-2022 | indéterminé | ✓ non couvert | ✓ | 2/4 |
| axa-velo-cave-forcee | axa-optihome-2022 | couvert | ✗ indéterminé | ✓ | 9/11 |
| axa-vitre-porte-commune | axa-optihome-2022 | non couvert | ✗ indéterminé | ✓ | 3/3 |
| axa-portable-tombe | axa-optihome-2022 | couvert | ✓ couvert | ✓ | 5/5 |
| axa-bougie-jardin | axa-optihome-2022 | indéterminé | ✓ indéterminé | ✗ | 3/4 |
| axa-vol-porte-ouverte | axa-optihome-2022 | non couvert | ✓ non couvert | ✓ | 6/6 |
| lalux-velo-local-commun | lalux-easyprotect-2022 | indéterminé | ✗ non couvert | ✓ | 3/6 |
| lalux-machine-a-laver | lalux-easyprotect-2022 | couvert | ✓ couvert | ✓ | 4/5 |
| lalux-bougie-jardin | lalux-easyprotect-2022 | indéterminé | ✓ couvert | ✓ | 1/5 |
| lalux-cambriolage-fenetre | lalux-easyprotect-2022 | couvert | ✗ indéterminé | ✗ | 2/3 |
| lalux-vol-par-le-fils | lalux-easyprotect-2022 | non couvert | ✓ non couvert | ✓ | 3/3 |

Three design iterations, same 18 cases (one case = 5.5 points, so small differences are noise):

| Version | Verdict acceptable | Confident and wrong | Expected clause cited | Citations verbatim |
|---|---|---|---|---|
| 1. Model writes the verdict | 67 % | 0 % | 56 % | 61 % |
| 2. + citation repair (markdown, neighbouring clause), "don't hedge" prompt | 56 % | 6 % | 83 % | 77 % |
| 3. Model reports findings, code derives the verdict, doubts must rest on the claim's words (deployed) | 61 % | 11 % | 83 % | 76 % |

What the numbers say: the grounding works and the reasoning is the bottleneck. Four answers in five rest
on the clause a human marked as decisive, and three citations in four are found word for word (the rest are
shown as unverified, never silently used). Version 1 never answered confidently and wrongly, but only because
it hedged on almost everything, including a washing-machine leak. Version 3 answers the clear cases
more often and puts the decision rule in code where it can be read and tested, at the cost of two confident
errors: the Baloise candle (it read sun-melted wax as "action subite de la chaleur") and the Lalux
bike (it applied an exclusion about valuables and cash left in the cellars of apartment buildings, a
sentence that segmentation had also split across a page break, and assumed the bike was not locked, which
the claim does not say). With ministral-14b, results also move between runs at temperature 0, so the next steps are a stronger model and
three runs per case with a majority vote, then a larger labelled set written with claims handlers.

## Limits

- **The general conditions are not the contract.** Options, ceilings and deductibles live in the
  *Conditions Particulières*, which are not public. The app assumes the relevant option is subscribed and
  says which one to check.
- **A small model.** The live demo runs on `ministral-14b` (the free Mistral tier gives no access to larger
  models). Segmentation is sometimes too coarse, some labels are wrong, and the reasoning makes mistakes
  that the checks catch only partly: a verified quote can still be applied to the wrong situation. The
  model is one setting (`MISTRAL_MODEL`); the evaluation is how to tell whether a bigger one is worth it.
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

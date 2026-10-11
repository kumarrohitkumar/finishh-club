# R2 — High Level Design

**Version 1.0** · 20 Sep 2026 · Follows `HLD.md` (R1).

---

## 1. The headline

**Almost nothing changes.**

R1's HLD named four extension points and claimed future work would plug into them without rewriting. R2 is the test of that claim. Here is the honest accounting:

| R2 feature | New tables | Changes to existing code |
|---|---|---|
| Hybrid search | none | `knowledge/search.py` only |
| IPOs | `ipos`, `ipo_subscriptions` | none |
| DRHP search | none — uses `documents.collection` | none |
| Collection | `saved_assets` exists, add `lists` | none |
| Login | `users`, `sessions`, `otp_codes` exist | none |
| Isaa memory | `conversations`, `messages` | the loop gains a history parameter |
| Portfolio | `holdings` | none |

**Nothing in `meter/`, `adapters/`, `ingest/` or `db/repository.py` is touched.**

If that stops being true while building, stop and say so — it means R1's design was wrong somewhere, and that is worth knowing.

---

## 2. Phase A — hybrid search

### 2.1 What exists now

```
question → websearch_to_tsquery → ts_rank → top 3 → Isaa
```

One SQL query. `documents.embedding` exists and is empty. pgvector is installed.

### 2.2 What it becomes

```
                      question
                          │
              ┌───────────┴───────────┐
              │                       │
       keyword search          embed the question
       (ts_rank)                      │
              │                vector search
              │                (cosine distance)
              └───────────┬───────────┘
                          │
                  combine the scores
                          │
                      top 3 → Isaa
```

### 2.3 How the two scores combine

They are not comparable numbers — `ts_rank` and cosine similarity live on different scales. Averaging them raw is meaningless.

**Reciprocal Rank Fusion.** Each search produces a ranked list. A document scores by its *position*, not its raw score:

```
score(doc) = Σ  1 / (k + rank in that list)        k = 60, conventional
```

Why this and not weighted averaging: it needs no normalisation, no tuning of incomparable scales, and it is robust when one search returns nothing at all — which is exactly our 36% case.

`HS-5` asks for one tunable number. That is `k`, plus an optional weight per list.

### 2.4 Where embedding happens

```
knowledge/pipeline.py   loads a file
     │
     ├── content unchanged?  → skip embedding (HS-2)
     └── changed or new?     → embed once, store
```

A content hash on the row decides. Filings are long; re-embedding unchanged text is money for nothing.

### 2.5 Embedding provider

One function, one place:

```
knowledge/embed.py     embed(texts) -> list[vector]
```

OpenAI or a local model behind the same call. The dimension is a constant, not scattered. Switching provider means re-embedding everything, so the migration that changes the vector column is part of that change, not a surprise.

### 2.6 What must not change

`search_concepts` still returns `title` and `content` only. **No numeric fields.** Hybrid search changes how documents are found, never what a document is allowed to contain.

---

## 3. Phase B — IPOs

### 3.1 Why IPOs are not assets

Tempting to put them in `assets` — they are not. An asset in this system is *a thing with a price series*. An IPO has no price until it lists.

```
assets           has price_history, has meter_results
ipos             has dates, a band, subscription. No meter, ever.
```

Forcing them into `assets` would mean nullable price columns and a meter that must be suppressed. Cleaner to keep them apart.

**When an IPO lists**, it becomes a row in `assets` with `asset_type='stock'` (R3) and the `ipos` row keeps a reference. Two records, two lifecycles, one link.

### 3.2 New tables

```
ipos
  id, company_name, plain_summary, price_band_low, price_band_high,
  lot_size, issue_size, open_date, close_date, listing_date,
  status (upcoming | open | closed | listed),
  listed_asset_id  → assets(id), null until it lists

ipo_subscriptions
  ipo_id, as_of, category (qib | nii | retail | total), times_subscribed
```

Subscription is a time series, so it is its own table. Same reasoning as prices.

### 3.3 DRHP chunks reuse `documents`

No new table. This is extension point 4 doing its job:

```
documents
  collection = 'concepts'   32 short, hand-written    ← today
  collection = 'drhp'       thousands, machine-split  ← R2
  metadata   = {ipo_id, section, page}
```

`metadata` is already `jsonb`. Filtering to one IPO's filing (DRHP-4) is a `WHERE` on it.

### 3.4 Chunking — where the real work is

32 short documents hid this problem. A 400-page filing does not.

| Decision | Why it matters |
|---|---|
| Split on section headings, not fixed characters | "Risk Factors" must not be cut in half |
| Keep the heading text on every chunk | The chunk stays meaningful alone, and it is what gets cited |
| Overlap between chunks | A sentence spanning a boundary is otherwise lost by both |
| Target size | Too small loses context, too large dilutes the embedding |

**None of these are guessable.** DRHP-6 requires a 20-question eval so chunk size is chosen by measurement, not opinion. Expect two or three attempts.

### 3.5 New Isaa tools

```
DATABASE (numbers)          RETRIEVAL (prose)
  get_ipo                     search_filing(ipo_id, question)
  get_ipo_subscription
  list_ipos
```

The boundary holds. Subscription percentages come from the database. "What does this company do" comes from the filing.

---

## 4. Phase D — login and memory

### 4.1 Sessions

R1 chose Postgres over Redis for one user. That stands until there are real users. The decision is one file (`db/connection.py` plus a sessions helper), so it moves later without touching routes.

### 4.2 Memory has two halves

You built both in the learning project:

```
conversations / messages    recent turns, TRIMMED       ← agent_chat.py
user_facts                  durable, NEVER trimmed      ← agent_memory.py
```

The loop gains a `history` parameter. Facts are injected into the system prompt, as before.

**MEM-6 is an architectural rule, not a preference:** memory may change Isaa's wording. It must never reach the Meter, a NAV, or any number. Those come from tools that do not know a user exists.

---

## 5. What stays exactly as it is

| | |
|---|---|
| `meter/engine.py` | untouched. It takes a price series and knows nothing else |
| `adapters/` | untouched until R3 stocks |
| `ingest/` | gains an IPO adapter; the AMFI path is unchanged |
| `db/repository.py` | gains functions, changes none |
| The loop | gains a parameter |
| The four safety rules | unchanged and non-negotiable |

---

## 6. Deployment changes

| | |
|---|---|
| Hybrid search | none — pgvector is already installed |
| Scheduled refresh | one GitHub Actions secret |
| DRHP storage | thousands of chunks with embeddings. **Watch the 0.5 GB Neon limit** |
| Login | none, until real users make Redis worth adding |

**A real number to watch:** one DRHP is roughly 2,000 chunks. At 1536 dimensions that is about 12 MB of vectors per filing. Twenty filings is 240 MB — half your free tier. Either store fewer filings, use a smaller embedding, or budget for a paid tier. Decide before ingesting the twentieth.

---

## 7. Build order, and why

```
A  hybrid search        small, self-contained, measurable
   scheduled refresh    10 minutes, stops the data rotting
B  IPO tables + pages   no dependency on A, but A makes the search good first
   DRHP chunking        the hard part. Needs A's retrieval to be trustworthy
C  Collection           small
D  Login → memory       memory is pointless without accounts
E  Portfolio            needs D
```

A before B on purpose: debugging chunk size on top of a retrieval layer you already measured is tractable. Debugging both at once is not.

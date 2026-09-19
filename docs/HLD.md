# Finishh club — High Level Design (HLD)

**Version 1.0** · 18 Sep 2026 · Covers R1, designed so R2 and R3 slot in without rewriting.

This document says **what the pieces are and how they talk**. The LLD says what is inside each piece.

---

## 1. The one design rule

> **Build for assets, not for funds.**

A mutual fund and a stock are the same thing to this system: a name, a category, and a series of prices over time.

If we write `funds` everywhere in R1, then adding stocks in R3 means changing every table, every query and every function. If we write `assets` with a type field, adding stocks means **inserting rows**, not changing code.

This single choice is what makes R2 and R3 cheap.

| We do NOT write | We write |
|---|---|
| `funds` table | `assets` table with `asset_type` |
| `nav_history` table | `price_history` table |
| `get_fund_meter()` | `get_meter(asset_id)` |
| AMFI parser inside the ingest job | An AMFI **adapter** behind a shared interface |

---

## 2. The system

```
   ┌───────────────┐
   │  React (SPA)  │  browser
   └───────┬───────┘
           │ HTTPS
   ┌───────▼────────────────────────────────────┐
   │              FastAPI                       │
   │  ┌──────┐ ┌──────┐ ┌──────┐ ┌───────────┐  │
   │  │ auth │ │assets│ │meter │ │   isaa    │  │
   │  └──────┘ └──────┘ └──────┘ └───────────┘  │
   └───┬───────────┬──────────────────┬─────────┘
       │           │                  │
   ┌───▼───┐   ┌───▼──────────────────▼────────┐
   │ Redis │   │      Postgres 16 + pgvector   │
   │       │   │  assets · price_history       │
   │sessions│  │  meter_results · users        │
   │ cache │   │  documents (+ embeddings)     │
   └───────┘   └───▲───────────────────▲───────┘
                   │                   │
        ┌──────────┴────────┐   ┌──────┴──────────┐
        │  Ingestion job    │   │  Meter job      │
        │  (daily, 23:00)   │   │  (nightly)      │
        └──────────┬────────┘   └─────────────────┘
                   │
        ┌──────────▼─────────────────────────┐
        │  Source adapters                   │
        │  AMFI (R1) · NSE (R3) · paid (R3)  │
        └────────────────────────────────────┘
```

---

## 3. The components

| Component | Job | Knows about |
|---|---|---|
| **Source adapters** | Fetch from one outside source, return normalised records | That one source only |
| **Ingestion job** | Run adapters, validate, write to `price_history` | Adapters and the database |
| **Meter engine** | Pure calculation: price series → bucket percentages | Nothing. No database, no network |
| **Meter job** | Run the engine over every asset nightly, save results | Engine and database |
| **API** | Serve data over HTTP, handle auth | Database, Redis |
| **Isaa service** | Agent loop, tools, document search | Database via tools |
| **Knowledge pipeline** | Documents → chunks → embeddings → pgvector | Documents and the database |
| **Postgres** | All durable data, including vectors | — |
| **Redis** | Sessions and cache | — |

**The Meter engine is deliberately pure.** It takes a list of (date, price) and returns numbers. It does not know what a mutual fund is. That is why it will work unchanged for stocks in R3 and for whole portfolios later.

---

## 4. Data flows

### 4.1 Write path — daily

```
23:00  Ingestion job
         → AMFI adapter downloads the NAV file
         → parse into normalised records
         → validate  (row count check, rule D-4)
         → upsert into assets + price_history

23:30  Meter job
         → for each asset, for each period (1Y/3Y/5Y)
             → load price series
             → engine computes distribution
             → write meter_results
```

Nothing is computed while a user is waiting.

### 4.2 Read path — a user opens a fund page

```
GET /assets/{id}          → Postgres, one row
GET /assets/{id}/meter    → meter_results, one row  (already computed)
```

Both are simple lookups. This is how we hold the 400 ms target (rule N-1).

### 4.3 Isaa path — and why it forks

This is the most important flow in the system.

```
             user question + page context
                        │
                ┌───────▼────────┐
                │   agent loop   │
                └───────┬────────┘
                        │  model picks a tool
          ┌─────────────┴──────────────┐
          │                            │
   ┌──────▼───────┐            ┌───────▼────────┐
   │ DATABASE     │            │ DOCUMENT       │
   │ TOOLS        │            │ SEARCH (RAG)   │
   │              │            │                │
   │ get_asset    │            │ search_        │
   │ get_meter    │            │   concepts     │
   │ get_price    │            │                │
   │ compare      │            │                │
   └──────┬───────┘            └───────┬────────┘
          │                            │
      NUMBERS                     EXPLANATIONS
      exact, current              prose only
          │                            │
          └─────────────┬──────────────┘
                        │
              structured reply
              (answer + claims + sources)
```

**Two paths, and they never cross.**

Numbers come from the left side. Explanations come from the right side. A number must never arrive from the right side — a document can be old, and a model can misread it. Saying an expense ratio is 0.5% when it is 1.8% is real harm.

This is enforced twice: by giving the search tool no numeric fields, and by test E-2 which traces every number in a reply back to a tool call.

---

## 5. How R2 and R3 slot in

This is the point of the design. Each future feature is an **addition**, not a change.

| Future feature | What you add | What you change |
|---|---|---|
| **Stocks (R3)** | An NSE adapter. Rows with `asset_type='stock'`. A `stock` bucket scale | **Nothing.** Meter engine, API and Isaa tools already work on assets |
| **IPOs (R2)** | An `ipos` table and adapter. An IPO API route | Nothing existing. IPOs have no price history so they skip the Meter entirely |
| **DRHP search (R2)** | Documents with `collection='drhp'` | Nothing. Same pipeline, same table, filter by collection |
| **Portfolio (R2)** | `holdings` table. A `get_portfolio` tool | Nothing. Isaa gains one tool entry |
| **Isaa memory (R2)** | A `conversations` table, loaded before the loop | The loop keeps its shape |
| **Portfolio Meter (R3)** | A function that blends holdings into one weighted series | Nothing in the engine — it still just takes a series |
| **SIP mode (R3)** | A second calculation inside the engine | Same inputs, same outputs |
| **New data source** | A new adapter class | Nothing. The interface is fixed |

### The four extension points, named

1. **`SourceAdapter`** — one method, `fetch() -> list[PriceRecord]`. Add a source by adding a class.
2. **`assets.asset_type`** — fund, stock, index. Add a type by adding rows.
3. **`TOOLS` registry** — a dictionary name → function. Add an Isaa ability with one entry. *(Same pattern you already use in `agent_files.py`.)*
4. **`documents.collection`** — concepts, drhp, methodology. Add a knowledge area with a new value.

> If a future feature needs a change **outside** these four points, that is a signal the design was wrong — stop and reconsider before writing it.

---

## 6. Technology, and why

| Layer | Choice | Reason |
|---|---|---|
| API | FastAPI | Async, and Pydantic is built in — we need Pydantic anyway for Isaa's structured replies |
| Database | Postgres 16 | Time-series price data is relational. Joins matter here |
| Vectors | **pgvector**, not a separate vector database | One database to run and back up. Document text and its embedding live in the same row |
| Sessions | Redis | Must be revocable instantly (rule A-10). A JWT cannot be cancelled |
| Cache | Redis | Meter reads and repeated concept answers |
| Jobs | APScheduler | Two nightly jobs. Celery is more machinery than this needs |
| LLM | OpenAI API | Chosen by the owner |
| Embeddings | `text-embedding-3-small` | Cheap, good enough for short concept documents |
| Frontend | **React + Vite** | Single-page app, built to static files. Simpler than Next.js, and we do not need server rendering for a personal app |

**Why not a separate vector database:** we have thousands of concept chunks, not millions. pgvector handles that easily, and keeping one database means one connection, one backup, one thing to operate. Adding Pinecone here would be a second system bought for no benefit.

---

## 7. Where things live in the repo

```
finishh-club/
├── docs/                PRD · R1_PLAN · HLD · LLD
├── adapters/            one file per source
│   ├── base.py          SourceAdapter interface
│   └── amfi.py          R1
├── ingest/              the daily job
├── meter/
│   ├── engine.py        pure calculation, no I/O
│   ├── buckets.py       category scales
│   └── job.py           nightly runner
├── api/
│   ├── auth.py  assets.py  meter.py  isaa.py
├── isaa/
│   ├── loop.py          the agent loop
│   ├── tools.py         database tools registry
│   ├── retrieval.py     document search
│   └── schema.py        Pydantic reply contract
├── knowledge/
│   ├── concepts/        the written documents
│   └── pipeline.py      chunk → embed → store
├── evals/               E-1 to E-4 suites
├── tests/
└── frontend/
```

**`meter/engine.py` imports nothing from the rest of the project.** That is intentional. It keeps the riskiest calculation testable in isolation and reusable for stocks and portfolios.

---

## 8. Failure handling

| If this fails | What happens |
|---|---|
| AMFI download fails | Job retries with backoff. Yesterday's data stays. Alert raised |
| Today's file looks wrong (rule D-4) | Job stops, writes nothing, alerts. Never overwrites good data with bad |
| Meter job fails mid-run | Per-asset writes, so completed assets stay. Resumable |
| A Meter has too little history | Row still written with `insufficient_history` flag. UI shows the explanation, never an empty bar |
| OpenAI is down | Isaa returns a clear error. The rest of the site works — fund pages do not depend on the model |
| Redis is down | Users are logged out. Fund browsing still works |

**Isaa is not on the critical path.** If the model is unavailable, the product still shows funds and Meters. That is deliberate.

---

## 9. What we are consciously not doing

| Not doing | Why |
|---|---|
| Microservices | One API process. Splitting adds deployment work and solves nothing at this size |
| Kafka | Two nightly jobs. A scheduler is enough |
| Kubernetes | One container each for API, jobs and frontend |
| Separate vector DB | pgvector is sufficient and is one less system |
| Real-time prices | Costly, and it contradicts the product idea (PRD §12) |

These are all things to add **if a real problem appears**, not before.

---

Next document: **LLD** — table definitions with columns and indexes, API request and response shapes, the adapter interface, the Isaa tool signatures, and the Pydantic reply schema.

# Finishh club

An app that explains Indian mutual funds, IPOs and stocks in plain English.
It never tells anyone what to buy.

**Status:** R1 backend and web app complete. 74 tests passing.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/kumarrohitkumar/finishh-club)

See [DEPLOY.md](DEPLOY.md) for the three steps.

---

## Run it

Two terminals.

```bash
# 1. the API
uvicorn api.main:app --reload          # http://127.0.0.1:8000/docs

# 2. the website
cd frontend && npm run dev             # http://localhost:5173
```

Other things:

```bash
python -m db.migrate                   # create or update tables
python -m ingest.seed 25               # load funds from AMFI
python -m ingest.daily                 # today's NAV for funds we hold
python -m meter.job                    # recompute every meter
python -m knowledge.pipeline           # load concept documents
python -m isaa.loop "is this risky?" --fund 119507

python -m evals.retrieval              # concept search recall
python -m evals.isaa_eval --quick      # Isaa refusal / grounding

for t in tests/test_*.py; do python $t; done
```

---

## Every file, and what it is for

### The code

| File | What it does |
|---|---|
| `step0.py` | **Start here.** One fund, end to end: fetch → compute Meter → print |
| `constants.py` | Fixed values that describe the product — buckets, categories, periods |
| `config.py` | Settings that differ per machine — URLs, timeouts. All from environment variables |
| `meter/buckets.py` | The numbers that decide green / orange / blue / red, per category |
| `meter/engine.py` | **The Meter calculation.** Pure maths. Imports nothing from this project |
| `adapters/base.py` | The shape every data source must fit. Extension point for stocks later |
| `adapters/amfi.py` | Fetches Indian mutual fund data from AMFI |

### The tests

| File | Covers |
|---|---|
| `tests/test_engine.py` | The Meter maths. 10 tests. **The most important ones** |
| `tests/test_amfi.py` | Category mapping and bad-row handling. 12 tests. No network |
| `tests/test_slice.py` | The glue between adapter and engine. 4 tests |

### The documents

| File | Answers |
|---|---|
| `docs/PRD.md` | What we are building, and what we are not |
| `docs/R1_PLAN.md` | The build order, step by step |
| `docs/HLD.md` | How the pieces fit, and how R2/R3 slot in later |
| `docs/DATABASE.md` | Tables and diagram |
| `docs/DEPLOYMENT.md` | Running it for ₹0 |

---

## How data moves

```
   AMFI website
        │
        ▼   adapters/amfi.py       fetch and clean
        │
   PriceRecord list                (date, price) pairs
        │
        ▼   meter/engine.py        the calculation
        │
   MeterResult                     four percentages, adding to 100
        │
        ▼   step0.py               print it
```

Later, the database sits between the adapter and the engine, and the API and
React frontend replace the printing. **The middle does not change.**

---

## Three rules the code follows

**1. Constants live in one place.**
`constants.py` for product values, `config.py` for machine values. No numbers
typed into logic.

**2. The Meter engine is isolated.**
It imports nothing from this project. No database, no network. That makes it
testable on its own, and it will work unchanged for stocks and portfolios.

**3. A new data source is a new class, nothing else.**
Everything returns `PriceRecord`, so the engine never learns where a price came
from. If adding a source ever requires changing something else, the design is
wrong.

---

## Where the Meter numbers come from

```
Equity   green above 10%/yr    Debt   green above 8%/yr
         orange 4-10%                 orange 6-8%
         blue 0-4%                    blue 0-6%
         red below 0%                 red below 0%
```

Debt funds rarely exceed 10% a year. On the equity scale every debt fund would
look bad while working perfectly normally. This is why the scale in use is
always shown on screen.

---

## Next

Step 1 — Postgres and pgvector in Docker, the tables from `docs/DATABASE.md`,
then ingest all 1,828 Direct-Growth funds instead of one.

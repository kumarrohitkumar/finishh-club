# R1 — Implementation Plan

**Goal of R1:** one person can open the app, browse mutual funds, see the Finishh Meter, and ask Isaa questions about a fund. Free data only. No stocks.

**How we build:** thin slice first, then widen. We get one fund working end to end before we do all 8,615.

---

## Step 0 — The thin slice (do this first)

Before building any layer properly, get **one fund** working from download to screen.

```
download 1 fund's history
   -> save to database
   -> calculate its Meter
   -> serve it from an API
   -> print it in the terminal
```

**Why this first:** if something is wrong in the idea — data format, Meter maths, a missing field — you find out in a day instead of week three.

**Done when:** you can run one command and see a real Meter for a real fund.

---

## Step 1 — Setup and database

**Build**
1. Folder structure, virtual environment, dependency file
2. Postgres 16 with pgvector, running in Docker
3. Redis, running in Docker
4. One `docker compose up` starts both
5. Database tables created by a migration file

**Tables in R1**

| Table | Holds |
|---|---|
| `schemes` | scheme code, name, fund house, category, plan, option |
| `nav_history` | scheme code, date, nav |
| `meter_results` | scheme code, period, bucket percentages, window count, computed time |
| `users` | email, password hash, state, created time |
| `sessions` | handled in Redis, not Postgres |
| `concepts` | concept text + embedding (used in Step 6) |

**Done when:** `docker compose up` gives you a working database with empty tables.

**Watch out:** `nav_history` will hold roughly 20-30 million rows. Index on `(scheme_code, date)` from the start, not later.

---

## Step 2 — AMFI download

**Build**
1. Daily job: download `portal.amfiindia.com/spages/NAVAll.txt`, parse, insert
2. Category parser — the file has section headers like `Open Ended Schemes(Equity Scheme - Large Cap Fund)`. That is where equity / debt / hybrid comes from
3. History backfill: fetch date ranges from AMFI's history endpoint, month by month
4. Safety check: if today's file has 5% fewer funds than yesterday, stop and alert (rule D-4)

**Done when:** database has all schemes with categories, and full NAV history.

**Watch out**
- The URL is `portal.amfiindia.com`, not `www.amfiindia.com` — the old one redirects
- The file has 8 columns now, not the 6 you see in older examples
- Backfill is thousands of requests. Run it once, slowly, with retries. Save raw files so you never have to re-download
- Some rows have no NAV. Skip and log them. Never write zero (rule D-6)

---

## Step 3 — Finishh Meter engine

**This is the most important step. A bug here is not a display bug — it is wrong financial information.**

**Build**
1. A pure function: NAV series + period + category scale → bucket percentages
2. Tests before anything else, with hand-calculated answers
3. Nightly job that computes all schemes and writes `meter_results`

**Tests that must exist**

| Test | Checks |
|---|---|
| Known CAGR | 100 → 200 over 5 years must give 14.87% per year |
| Buckets total 100 | After rounding, always exactly 100 |
| Daily stepping | A 10-year series gives the expected number of 5-year windows |
| Too young | A 2-year-old fund asked for 5Y falls back to 2Y with the explanation |
| Under 30 windows | Shows "not enough history", not an empty bar |
| Gaps | Weekends and holidays do not break window alignment |
| Debt vs equity | The same returns bucket differently on the two scales |

**Done when:** all tests pass and a real fund's Meter looks sensible against its published returns.

**Watch out:** windows step by **day**, not month (rule M-1). Returns are **per year**, not total (rule M-2).

---

## Step 4 — Fund API

**Build**

| Endpoint | Returns |
|---|---|
| `GET /funds` | List with filters — category, house, search |
| `GET /funds/{code}` | Detail: name, house, category, description, latest NAV |
| `GET /funds/{code}/meter?period=3Y` | Bucket percentages, scale used, window count, data period |
| `POST /funds/{code}/save` | Save to Collection |

**Done when:** every endpoint returns correct data, and the Meter read is a straight table lookup — never calculated live (rule N-2).

---

## Step 5 — Login

**Build**
1. Signup: email + password → account created unverified
2. Email a 6-digit code, verify it, mark active
3. Login, logout, logout-everywhere
4. Sessions in Redis with an httpOnly cookie
5. Google sign-in
6. Password reset
7. Delete account

**Done when:** you can sign up, get the code, log in, see your sessions, and delete your account completely.

**Watch out:** rules A-1 to A-16 in the PRD. The easy ones to forget are A-7 (never reveal whether an email exists) and A-13 (never silently merge a Google account with an existing one).

---

## Step 6 — Concept knowledge base

**Build**
1. Write about 50 short concept documents in plain English — NAV, expense ratio, AUM, exit load, XIRR, CAGR, SIP, lump sum, risk levels, benchmark, drawdown, direct vs regular, and so on
2. Split them, embed them with OpenAI, store in pgvector
3. A search function that returns the best matches
4. A labelled question → correct document list, for measuring recall (rule E-4)

**Done when:** searching "what is expense ratio" returns the expense ratio document, and recall on your labelled set is 85% or better.

**Watch out:** write the labelled question set **before** tuning the search. Otherwise you will tune until it looks good rather than until it is good.

---

## Step 7 — Isaa

**You already know how to build this.** It is the same agent loop from `agent_groq.py`.

**Build**
1. The loop — you have written it four times already
2. Database tools: `get_fund`, `get_meter`, `get_nav`, `compare_funds`
3. One search tool: `search_concepts`
4. Page context attached automatically (rule I-9)
5. Structured reply using Pydantic — answer, claims, confidence, unknowns, tools used
6. System prompt: no verdicts, never guess, cite sources

**Done when:** "is this fund risky?" on a fund page returns a grounded answer citing its source, and "should I buy this?" is refused.

**Watch out:** the boundary from PRD §7.1. **Numbers come from database tools. Search is for explanations only.** If a number ever comes out of the document search, that is a bug, not a style choice.

---

## Step 8 — Tests for Isaa

**Build**
1. Refusal suite — 40 buy/sell questions including Hinglish. Must pass 100%
2. Grounding suite — every number traced to a tool call. Must pass 100%
3. Hallucination suite — ask about funds that do not exist. Must say "I do not know". 100%
4. Retrieval suite — recall@5, target 85%
5. One command runs all four and prints a score

**Done when:** all four run in one command and the first three are at 100%.

**You already have the harness** — `eval_run.py` from your learning project is the same shape.

---

## Step 9 — Frontend

**Build**
1. Explore page — Ask Isaa bar, Mutual Funds tile, one rail
2. Fund list with filters
3. Fund detail page in the PRD order, details collapsed
4. The Meter component — bars, scale always visible, period switch, "Why?"
5. Isaa floating button and overlay
6. Login screens

**Done when:** you can do the whole journey in a browser without touching the terminal.

**Watch out:** no chart renders by default (rule F-3). Details start collapsed. The Meter scale is always on screen (rule M-6).

---

## Order and dependencies

```
0. thin slice
      │
1. setup + database
      │
2. AMFI download ──────► 3. Meter engine
      │                        │
      └──────────┬─────────────┘
                 │
            4. Fund API ────► 9. Frontend
                 │                 ▲
5. Login ────────┘                 │
                                   │
6. Concepts ──► 7. Isaa ──► 8. Tests
```

**Can be done in parallel:** Step 5 (login) does not depend on funds. Step 6 (concepts) is just writing documents — start it early, in gaps.

---

## If time runs short

Build in this order and stop wherever you run out. Every stopping point still leaves something that works.

| Priority | Steps | What you have if you stop here |
|---|---|---|
| 1 | 0, 1, 2, 3 | Meter working on real data, in the terminal. **The hard part is done** |
| 2 | 4 | An API you can call |
| 3 | 7, 8 | Isaa answering fund questions, with tests |
| 4 | 9 | Something you can show on a screen |
| 5 | 5, 6 | Login and concept search |

**Login is last on purpose.** For personal use you do not need it to prove anything works. It is required by the PRD for a real product, not for a working prototype.

---

## The three risky parts

| Risk | Why | What to do |
|---|---|---|
| History backfill is slow and fiddly | Thousands of requests, format changes over the years | Save every raw file. Never re-download. Make it resumable |
| Meter maths is wrong | A quiet error produces confident wrong numbers | Tests first, with hand-calculated values |
| Frontend takes longer than expected | Backend is your strength | Plain and simple. Styling waits for the reference images |

---

## What we are NOT doing in R1

Stocks · IPOs · Portfolio · Collection lists · Compare · Isaa memory · personalisation · notifications · calculators · search · SIP mode in the Meter · CAS upload.

All of it is written down in the PRD. None of it is forgotten. It is just not now.

# Deployment Plan — free tier

**For personal use.** Everything here is free except OpenAI, which costs a few rupees a month at personal volume.

> Free tier limits change often. Check current limits before relying on any number here.

---

## 1. The constraint is storage, not servers

Measured from the real AMFI file:

**Measured, not estimated.** One real fund was loaded into Neon and the table
size read back: **121 bytes per row** including indexes (61 data + 36 index +
overhead). An earlier estimate of 40 bytes was 3x too low.

**Neon free plan: 0.5 GB per project** (5 GB aggregate across up to 10 projects).

| What we store | Funds | Rows | Size | Fits 0.5 GB? |
|---|---|---|---|---|
| Everything AMFI publishes | 14,375 | 47.4M | 5.76 GB | no |
| All Direct + Growth, 13y | 1,828 | 6.0M | 0.73 GB | no |
| Equity + hybrid, 13y | 1,168 | 3.9M | 0.47 GB | too tight |
| **Equity + hybrid, 10y** | **1,168** | **3.0M** | **0.36 GB** | **yes** |
| Equity only, 13y | 932 | 3.1M | 0.37 GB | yes |

**Why the big drop:** AMFI lists the same fund many times — Direct and Regular plans, Growth and IDCW options. They are not different funds. Keeping only **Direct + Growth** gives 1,828 real funds.

This is also the right product decision. Direct plans have lower expense ratios, so a product that explains investing should show those.

### Rule
```
Ingest only:  Plan = Direct  AND  Option = Growth
              AND category in (equity, hybrid)
              AND history capped at 10 years
```

**Why these three filters**

1. **Direct + Growth** - AMFI lists the same fund many times (Direct/Regular x
   Growth/IDCW). They are not different funds. Direct plans also have lower
   expense ratios, so they are the right ones to show.
2. **Equity + hybrid** - a liquid or overnight fund's Meter is a single flat
   bar. Debt funds are the least useful thing to put a Meter on, and they are
   394 of the 1,828.
3. **10 years** - a 5-year Meter needs more than 5 years of data to have
   windows at all. 10 years gives about 1,300 five-year windows, which is
   plenty. 13 years would give 2,100 and cost 30% more storage.

**Anything not seeded is fetched on demand.** If a user opens a fund we do not
hold, fetch its history then and store it. The seed set is a head start, not a
limit.

---

## 2. Option A — run it on your own machine (simplest)

For personal use you may not need hosting at all.

```
docker compose up
```

- Postgres + pgvector in a container
- FastAPI running locally
- Next.js running locally
- Jobs on your Mac's scheduler

**Cost: ₹0.** No storage limits, no cold starts, no signups.

**Downside:** only works when your Mac is on, and only on your Mac.

**Do this for Steps 0-4 of the R1 plan.** Deploy only when you actually want it on your phone.

---

## 3. Option B — free cloud

| Piece | Service | Free tier | Why |
|---|---|---|---|
| Database | **Neon** or **Supabase** | ~0.5 GB, pgvector supported | 230 MB fits. pgvector is what we need |
| Backend API | **Render** free | Sleeps after 15 min idle | Cold start ~50 s. Fine for personal use |
| Frontend | **Vercel** / Netlify / Cloudflare Pages | Generous | A React build is static files. Any of these hosts it free |
| Scheduled jobs | **GitHub Actions** | 2,000 min/month | See §4 — this is the neat part |
| Sessions | **Postgres**, not Redis | — | See §5 |
| LLM | OpenAI | Paid, tiny | See §6 |

```
   phone / laptop
        │
   ┌────▼─────┐
   │  Vercel  │   React static build
   └────┬─────┘
        │
   ┌────▼─────┐
   │  Render  │   FastAPI   (sleeps when unused)
   └────┬─────┘
        │
   ┌────▼──────────────┐      ┌──────────────────┐
   │ Neon / Supabase   │◄─────│ GitHub Actions   │
   │ Postgres+pgvector │      │ daily ingest     │
   └───────────────────┘      │ nightly meter    │
                              └──────────────────┘
```

---

## 4. Jobs without a server

Render's free tier has **no cron jobs**. That is normally the thing that forces you onto a paid plan.

Use **GitHub Actions** instead. It is a scheduler that already runs for free.

```yaml
# .github/workflows/daily.yml
on:
  schedule:
    - cron: "30 17 * * *"     # 23:00 IST
jobs:
  ingest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -r requirements.txt
      - run: python -m ingest.daily
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
```

The job runs on GitHub's machine, downloads from AMFI, writes straight to Neon. **Your API server does not need to be awake.**

Same pattern for the nightly Meter job. Two workflow files, no server, no cost.

**Watch out:** GitHub disables scheduled workflows after 60 days of no repository activity. Push something occasionally, or run it manually once in a while.

---

## 5. Drop Redis for personal use

The PRD wants Redis for sessions because revoking must be instant (rule A-10). That is correct for a public product.

For personal use with one user, Postgres does the same job:

| | Redis | Postgres sessions |
|---|---|---|
| Instant revoke | yes | yes |
| Speed | ~1 ms | ~5 ms |
| Extra service to run | yes | **no** |

One less service, one less free-tier signup, one less thing to break. Add Redis when there are real users and real load.

**Cache:** skip it. The Meter is already precomputed, which is where the speed comes from.

---

## 6. What it actually costs

| Item | Cost |
|---|---|
| Neon / Supabase | ₹0 |
| Render | ₹0 |
| Vercel | ₹0 |
| GitHub Actions | ₹0 |
| **OpenAI** | **the only real cost** |

**OpenAI estimate, personal use:**

```
embeddings: 50 concept docs, one time         ≈ ₹1
Isaa:       ~30 questions/day
            ~2,000 tokens in, 300 out each
            on a small model                  ≈ ₹30-60 / month
```

Under ₹100 a month, and only if you use it daily.

**To keep it low:** cache repeated concept answers (rule N-12), and use a small model — fund questions do not need the biggest one.

---

## 7. Limits you will actually hit

| Limit | Effect | What to do |
|---|---|---|
| Render sleeps after 15 min | First request takes ~50 s | Fine for personal. Or ping it every 10 min from the same cron |
| Neon free storage ~0.5 GB | Backfill fails partway | Direct+Growth filter. Then trim old daily data to weekly |
| GitHub Actions 2,000 min/mo | Jobs stop | Two short jobs use about 60 min/month. Not a problem |
| History backfill is thousands of requests | Slow, may be rate limited | Run it **once from your Mac**, not from Actions. Save raw files. Make it resumable |
| Free Postgres has no connection pooler on some tiers | Connection errors | Use the pooled connection string Neon provides |

---

## 8. Deployment order

Do not deploy early. Deploy when local stops being enough.

| When | Do this |
|---|---|
| R1 Steps 0-3 | **Local only.** Docker compose on your Mac |
| After Step 4 (API works) | Create the Neon database. Run backfill from your Mac into it |
| After Step 7 (Isaa works) | Deploy the API to Render |
| After Step 9 (frontend) | Deploy the React build to Vercel. **Set up the cookie/CORS pair first — see §11** |
| Any time after that | Move the two jobs to GitHub Actions |

**Backfill runs from your Mac, once.** It is thousands of requests and does not belong in a hosted job.

---

## 9. When it stops being personal

The moment a second person uses it, this plan needs to change:

| Change | Why |
|---|---|
| Add Redis for sessions | Real concurrency |
| Paid database tier | Storage and connection limits |
| Paid API tier | Cold starts become unacceptable |
| Rate limiting per user | Someone will burn your OpenAI budget |
| Backups | Losing personal data is annoying. Losing someone else's is serious |
| Re-read PRD §11 and §13 | Every legal item comes back |

Estimated cost at that point: roughly ₹2,000-4,000 a month before any stock data licensing.

---

## 10. Staying portable

Vercel now, anywhere later. That stays true only if we avoid provider-specific features.

| Layer | Portable choice | Lock-in to avoid |
|---|---|---|
| Frontend | A plain Vite build (`dist/` of static files) | Vercel Edge Functions, Vercel KV, Vercel Postgres, Vercel Analytics, image optimisation |
| Backend | A **Dockerfile** | Render-only build settings, Render-managed env magic |
| Database | Standard Postgres, plain SQL or SQLAlchemy, plain connection string | The Supabase client SDK, Supabase Auth, Supabase row-level-security as your auth layer |

**The test:** if moving hosts means editing application code, something provider-specific leaked in.
Moving should only mean changing a connection string and a deploy target.

Done this way:

```
React  -> static files   -> Vercel, Netlify, Cloudflare Pages, S3, your own nginx
API    -> Dockerfile     -> Render, Fly.io, Railway, any VPS
DB     -> Postgres dump  -> Neon, Supabase, RDS, your own Postgres
```

Each move is under an hour, with no code change.

**One that catches people:** Supabase Auth is genuinely good and genuinely hard to leave. Since the
PRD already specifies our own auth (rules A-1 to A-16), use Supabase as **just a Postgres database**
and nothing more.

---

## 11. React SPA — the cookie problem

This is the one thing plain React changes, and it only appears once you deploy.

**Locally it works fine.** `localhost:5173` (React) and `localhost:8000` (API) count as the
same site, so a normal `SameSite=Lax` cookie is sent.

**In production it breaks.** `your-app.vercel.app` and `your-api.onrender.com` are different
sites. The browser will not send a `SameSite=Lax` cookie across them, so every request looks
logged out.

### Two fixes

**Fix 1 — cross-site cookie (quick)**

```python
# FastAPI
response.set_cookie(
    key="session", value=sid,
    httponly=True, secure=True, samesite="none",   # "none" is required cross-site
)

app.add_middleware(CORSMiddleware,
    allow_origins=["https://your-app.vercel.app"],  # never "*" with credentials
    allow_credentials=True,
)
```

And on every fetch from React:

```js
fetch(url, { credentials: "include" })
```

**Fix 2 — one domain (better, when you have one)**

```
app.finishh.club   -> React
api.finishh.club   -> FastAPI
```

Both sit under the same registrable domain, so they are **same-site** and `SameSite=Lax`
works normally. This is stronger against CSRF and needs no `SameSite=None`.

### Rules
- `allow_origins` must be an explicit list. `"*"` with `allow_credentials=True` is rejected by browsers
- Never put the session token in `localStorage` — any script on the page can read it. Keep it an httpOnly cookie
- With `SameSite=None`, add a CSRF token on state-changing requests

### What else changes with React instead of Next.js

| | Effect |
|---|---|
| Server rendering | Gone. Irrelevant for personal use |
| SEO | Fund pages will not be indexed. Only matters if this goes public |
| Routing | React Router instead of file-based routes |
| Build output | Static files. Hostable anywhere, including Cloudflare Pages |
| Simplicity | **Fewer concepts to learn.** Good trade while the backend is the hard part |

---

## 11.5 Known issue - database region

**Measured 2026-09-18.** The Neon project sits in `aws-us-east-2` (Ohio).
From India the round trip is **296 ms**. The Meter computation itself is 9 ms,
so 99% of the nightly job is waiting for the network.

| Effect | Detail |
|---|---|
| Rule N-1 (API p95 < 400 ms) | **Not achievable.** One query costs 296 ms before any work |
| Nightly Meter job | 1.8 s per asset -> ~43 min for the full 1,434-fund seed |

**Fix:** recreate the project in `aws-ap-southeast-1` (Singapore) - the closest
region Neon offers to India, typically 60-90 ms. Roughly 4x faster.

A project's region cannot be changed, so this means a new project and a re-seed.
Deferred deliberately: it is cheap while the database holds 12 funds, and it
stays cheap until the API and frontend hold connection strings. **Do it before
the full seed.**

---

## 11.6 Known limit - Groq free tier token budget

**Measured 2026-09-19.** Groq's free tier allows **200,000 tokens per day, per
model**. A full run of the Isaa eval suite (37 questions, several tool steps
each) costs roughly 150,000 - so it can be run about once a day, and not at all
after normal development use.

| Limit | Value | Effect |
|---|---|---|
| Tokens per minute | 8,000 | The suite pauses and retries mid-run |
| Tokens per day | 200,000 | Roughly one full suite run per day |

**What we did**
- `python -m evals.isaa_eval --quick` runs a representative subset (~25k tokens)
  for everyday use. The full suite is for pre-release.
- The Isaa loop retries on 429 rather than failing, so a rate limit is a pause,
  not a broken eval.

**When this stops being enough:** move Isaa to OpenAI or Groq's paid tier. The
evals are the thing that needs headroom, not the product - a real user asks a
few questions, the eval suite asks forty.

---

## 12. Summary

1. Filter to **Direct + Growth** at ingestion. This is what makes free work
2. **Build locally.** Deploy only when you want it on your phone
3. Neon + Render + Vercel + GitHub Actions = ₹0
4. Skip Redis while it is personal
5. OpenAI is the only real cost, under ₹100/month
6. Run the one-time backfill from your own machine
7. React SPA needs the cookie/CORS pair sorted before deploy — see §11

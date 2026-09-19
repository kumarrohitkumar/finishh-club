# Finishh club — PRD (build version)

**Version 2.1** · 18 Sep 2026
Based on the product PRD by Ayush Sharma and Rohit Kumar.

This version is written to be built from. Short sentences. Every point numbered.

---

## 1. What we are building

An app that helps Indian people understand mutual funds, IPOs and stocks.

It explains things in plain English. It does not tell anyone what to buy.

- The user journey: **Find → Understand → Compare → Ask Isaa → Decide**
- The main feature: the **Finishh Meter**
- The AI assistant: **Isaa**

## 1.1 Current status — personal use

**Right now this is being built for personal use only. Not public. No other users.**

What that changes:

| Item | Status while personal |
|---|---|
| Written permission from AMFI | **Not needed.** Using public data for yourself is fine |
| SEBI advice rules | **Not applicable.** You cannot give yourself regulated advice |
| Legal review | **Not needed now** |
| Paid stock data | **Not needed.** Free sources are fine for personal use |

What does **not** change, and why:

1. **The R1/R2/R3 split stays.** That was never a legal question. The original scope was about eight months of work, and that danger is the same or worse for a personal project.
2. **The tests stay.** They are the strongest part of the work and cost little.
3. **The no-verdict design stays.** It is one line in a prompt. Keeping it means going public later is a decision, not a rewrite.

**The line that matters:** the moment a second person uses this, every rule in §11 comes back. Before anyone else gets access — even one friend — re-read §11 and §13.

---

## 2. What we are NOT building

1. No buying or selling
2. No holding of user money
3. No "you should buy this" advice
4. No guaranteed-return claims
5. No Hindi/Hinglish app screens — only Isaa replies in Hinglish

## 3. Rules that never change

These apply to every screen.

1. **Answer first, numbers second.** Every page opens with something a beginner understands.
2. **Details are hidden until asked.** One tap away. Never open by default.
3. **Explain, do not instruct.** Give facts and risks. Never a verdict.
4. **Never invent data.** If we do not have it, say "Not available".
5. **Show where data came from** and when it was updated.
6. **No chart opens by default.** Hard rule.
7. **Privacy controls must be easy to reach.** Not buried in settings.

---

## 4. The three releases

We build in three parts. R1 is small on purpose.

### R1 — Mutual funds only (uses free data)

| Area | What is in it |
|---|---|
| Data | Fund NAV from AMFI, daily + full history |
| Finishh Meter | Funds only. Lump sum only. 1Y, 3Y, 5Y |
| Funds | Browse, filter, detail page, save |
| Explore | Landing page, funds tile, Ask Isaa bar |
| Isaa | Page context, concept answers, database tools. No memory yet |
| Login | Email + password with OTP, Google sign-in |
| Privacy | See context, clear memory, delete account |
| Tests | Meter correctness, Isaa safety tests |

**R1 has no stocks.** Stock data costs money. AMFI fund data is free. So R1 costs nothing in data.

### R2 — IPOs, Collection, Portfolio

IPOs with GMP · IPO document search · Collection and Compare · Portfolio with **manual entry only** · Isaa memory · Search · Personalisation · Notifications · Calculators

### R3 — The heavy work

Stocks and Sectors (needs paid data) · CAS statement upload · Virtual Portfolio · SIP mode in the Meter · Push notifications

---

## 5. Requirements

### 5.1 Data (R1)

1. **D-1** Download the AMFI NAV file every day after 11 PM IST.
2. **D-2** On first setup, download the full history of every fund.
3. **D-3** Save scheme code, date, NAV and the time we downloaded it.
4. **D-4** If today's file has 5% fewer funds than yesterday, stop and alert someone. Do not overwrite good data with a broken file.
5. **D-5** Save each fund's category (equity, debt, hybrid). This decides which Meter scale to use.
6. **D-6** If a row cannot be read, log it and skip it. Never set it to zero.

### 5.2 Fund pages (R1)

1. **F-1** Show blocks in this order: name → Meter → good points and concerns → risk → then everything else closed.
2. **F-2** The page opens with the fund name, house, category and one plain-English line about it.
3. **F-3** No chart shows until the user opens a block.
4. **F-4** Every number shows its source and when it was last updated.
5. **F-5** Good points and concerns come from **fixed rules in code**, not from the AI. The AI can explain them but cannot write them.
6. **F-6** If a value is missing, show "Not available". Never blank, never zero, never an old value.

### 5.3 Login and accounts (R1)

**How signup works:**

```
user enters email + password
      -> account made, but not verified
      -> we email a 6-digit code
      -> user enters the code
      -> account active, user logged in
```

An unverified account can log in, but cannot open Portfolio, Collection or Isaa memory.

1. **A-1** Store passwords hashed with argon2id. Never store the real password.
2. **A-2** Password must be at least 10 characters. Reject common passwords.
3. **A-3** The email code is 6 digits, works once, expires in 10 minutes.
4. **A-4** Allow 5 wrong tries, then the code stops working.
5. **A-5** Allow 3 code resends per hour per email.
6. **A-6** After 10 failed logins, lock the account for 15 minutes.
7. **A-7** Never reveal whether an email is registered. Same message either way.
8. **A-8** Keep sessions in Redis. Use an httpOnly, Secure cookie.
9. **A-9** Session ends after 30 days idle, or 90 days total.
10. **A-10** The user can see all their logged-in devices and log any of them out.
11. **A-11** Changing password or email logs out every other device.
12. **A-12** Google sign-in only works with a verified Google email.
13. **A-13** If a Google email matches an existing account, ask for an email code before joining them. **Never join them silently.**
14. **A-14** Deleting an account removes login details, sessions, Isaa memory, portfolio and settings within 30 days. Access stops immediately.
15. **A-15** Password reset link works once and expires in 30 minutes. It logs out all devices.
16. **A-16** Log every login event with time and IP. **Never log passwords or codes.**

**Why Redis sessions and not JWT:** a JWT stays valid until it expires. You cannot cancel it. Isaa can see the user's portfolio, so "log out everywhere" must work immediately. A Redis session can be deleted instantly.

---

## 6. The Finishh Meter

### 6.1 What it is

It looks at the fund's own past NAV and answers one question:

> In the past, how often did this fund give each kind of result over this holding period?

It does **not** say what the user will get. It is history, not a forecast.

### 6.2 How it is calculated

1. User picks a holding period: 1, 3 or 5 years.
2. Take every possible window of that length in the fund's history, moving one day at a time.
3. For each window, work out the return **per year**.
4. Put each window into one of four groups.
5. Show the percentage in each group. They add up to 100%.

Formula for one window:

```
years      = (end date - start date) in days / 365.25
per year   = (end NAV / start NAV) ^ (1 / years) - 1
```

### 6.3 Rules

1. **M-1** Windows move one **day** at a time, not one month.
2. **M-2** Always show return **per year**, never total growth. This is what makes 1Y, 3Y and 5Y comparable.
3. **M-3** The four groups must add up to 100%. Put any rounding difference in the biggest group.
4. **M-4** Calculate every night and save it. Never calculate when the page loads.
5. **M-5** If the fund is too young for the chosen period, pick the longest period it can support and explain why. **Never show an empty bar.**
6. **M-6** Always show which scale is being used.
7. **M-7** Always show the data period and last update time.
8. **M-8** "Why?" opens an explanation below the meter. A public methodology page must exist.
9. **M-9** Need at least 30 windows to show a meter. Below that, show the "not enough history" message.

### 6.4 The four groups

Numbers are return **per year**. Each fund type gets its own scale.

| Fund type | Green | Orange | Blue | Red |
|---|---|---|---|---|
| Equity | above 10% | 4% to 10% | 0% to 4% | below 0% |
| Hybrid | above 10% | 5% to 10% | 0% to 5% | below 0% |
| Debt | above 8% | 6% to 8% | 0% to 6% | below 0% |
| Stocks (R3) | above 15% | 7% to 15% | 0% to 7% | below 0% |

**Why different scales:** a debt fund almost never gives more than 10% a year. If we judged it on the equity scale, every debt fund would look bad — when it is actually working normally.

### 6.5 Words we use

| Say this | Never say this |
|---|---|
| "70% of past periods" | "70% of people made profit" |
| "70% of observed outcomes" | "70% chance of profit" |
| "70% of rolling periods" | anything sounding like a prediction |

We do not have data about real investors. So we must not talk as if we do.

### 6.6 Where it applies

Funds (R1) · Stocks (R3) · Whole portfolios (R3).
**Never IPOs** — an IPO has no past price.

---

## 7. Isaa (the AI assistant)

### 7.1 The most important rule

Isaa can get information in two ways:

| Way | How | Use it for |
|---|---|---|
| **Database tool** | Isaa asks the database a question, gets an exact answer | **All numbers** |
| **Document search (RAG)** | Isaa searches our written documents | **Explanations only** |

> **Isaa must never take a number from document search.**

**Why:** a document can be old, and an AI can misread or invent a number. If Isaa says the expense ratio is 0.5% when it is really 1.8%, that is real money harm and our fault. The database is always correct and current.

| Data | Where it comes from |
|---|---|
| NAV, returns, expense ratio, AUM, risk level | Database tool |
| Finishh Meter values | Saved table, database tool |
| Portfolio totals (R2) | Calculated, database tool |
| "What is expense ratio?" | Document search |
| "What does this company do?" (R2) | Document search over IPO papers |
| Sector explanations, methodology | Document search |

### 7.2 Isaa rules

1. **I-1** Every number Isaa says must come from a tool call in that same answer.
2. **I-2** Isaa never searches the open internet. Only our own checked data.
3. **I-3** Isaa shows the source and time for any number it gives.
4. **I-4** Isaa separates: confirmed fact · calculated value · opinion · unknown.
5. **I-5** Isaa never says buy, sell or hold. (Until a lawyer approves otherwise.)
6. **I-6** If Isaa does not know something, it says so. It never guesses.
7. **I-7** Isaa may calculate freely using data we already have.
8. **I-8** Isaa replies in the user's language. **Financial terms and disclaimers stay in English.**
9. **I-9** Isaa already knows which page the user is on. "Is this risky?" works without naming the fund.

### 7.3 Testing Isaa

A rule written in a prompt is not a guarantee. The AI can ignore it. So we test it.

1. **E-1** 40 questions asking "should I buy this?" including Hinglish. Isaa must refuse **all 40**.
2. **E-2** Check every number Isaa says came from a tool. Must be **100%**.
3. **E-3** Ask about funds that do not exist. Isaa must say it does not know. Must be **100%**.
4. **E-4** Document search must find the right document at least **85%** of the time.
5. **E-5** These tests run automatically. If E-1, E-2 or E-3 fail, the release is blocked.
6. **E-6** Keep the test results for every release as proof.

If a regulator asks how we stop Isaa giving advice, the answer is "we test 40 cases every release", not "we wrote it in the prompt".

### 7.4 What Isaa returns

Not free text. A fixed structure:

```
answer        short plain English, can be expanded
claims[]      each one: value, source, time, came from tool or search
confidence    high / medium / low
unknowns[]    what was asked but we do not know
tools_used[]  record of what was called
```

---

## 8. Speed, cost and safety

### 8.1 Speed
1. **N-1** Fund page API must answer in under 400 ms (95% of the time).
2. **N-2** Meter is always read from the saved table. Never calculated live.
3. **N-3** Isaa starts replying within 2 seconds.
4. **N-4** The nightly Meter job finishes within 2 hours.

### 8.2 Data safety
1. **N-5** No financial data written into the frontend code.
2. **N-6** Official and unofficial data must look different on screen.
3. **N-7** Separate dev, staging and production environments.
4. **N-8** API keys stay on the server. Never in frontend code, URLs or logs.

### 8.3 AI cost
1. **N-9** Track what Isaa costs per user per month.
2. **N-10** Cache the parts of the prompt that never change.
3. **N-11** Give each user a daily limit on Isaa questions.
4. **N-12** Cache common concept answers so we do not pay twice for the same question.

---

## 9. How we know it is working

| What we measure | Target in R1 |
|---|---|
| Fund pages where the user opened a detail block | 35% or more |
| Sessions where the user asked Isaa something | 25% or more |
| Fund views where the user changed period or tapped "Why?" | 20% or more |
| Users who come back within 7 days | 20% or more |
| Isaa answers marked "not helpful" | 10% or less |
| Isaa refusing buy/sell questions | **100%** |

---

## 10. Where data comes from

| Data | Source | How often | Cost | Release |
|---|---|---|---|---|
| Fund NAV + history | AMFI | Daily | **Free to download. Commercial reuse to be confirmed — see risk 2b** | R1 |
| Fund details | AMFI + AMC sites | Weekly | Free | R1 |
| Concept explanations | We write them | Fixed | Free | R1 |
| IPO details | NSE, BSE, SEBI | Periodic | Mostly free | R2 |
| IPO documents (DRHP) | SEBI | Per IPO | Free | R2 |
| GMP | Unofficial sites | Periodic | **No licence — mark unofficial** | R2 |
| Stock prices | Paid provider, **15-min delayed** | Delayed | **Paid** | R3 |
| Company financials | Paid provider | Periodic | **Paid** | R3 |

**Display rules:** show last-updated time · show the delay · show "Not available" instead of fake or old data · mark unofficial data clearly.

---

## 11. Risks

| # | Risk | How bad | What we do |
|---|---|---|---|
| **0** | **Too much work. Project never finishes** | **Highest — most likely to kill it** | Split into R1/R2/R3. R1 is funds only |
| 1 | Isaa giving advice breaks SEBI rules | Very bad — **but not active while personal use only** | No verdicts. Tested at 100% every release. Turning it on later is only a prompt change |
| 2 | Using unlicensed data where users see it | Very bad | **R1 uses only free AMFI data, so there is no exposure until R3** |
| 2b | AMFI NAV is free to download, but commercial reuse is not confirmed in writing | Medium — **not active while personal use only** | Get written confirmation from AMFI before closed beta. Never use the AMFI logo. Always show "Source: AMFI" with the date |
| 3 | GMP has no legal standing | Medium | Mark unofficial, never the main card, never a prediction |
| 4 | People read the Meter as a forecast | Medium | Word rules, scale always visible, methodology page |
| 5 | Isaa invents a number | Very bad | Numbers only from database tools. Tested at 100% |

**About Risk 1:** telling a known user that a specific fund suits their goal is advice under Indian law. A disclaimer does not change that. So we ship with no verdicts.

---

## 12. Decisions made

| Question | Answer |
|---|---|
| Tech stack | Python 3.13 · FastAPI · Postgres 16 + pgvector · OpenAI API · Redis · **React (Vite)** |
| Meter numbers | Written in §6.4 |
| SIP mode in the Meter | Later (R3). Lump sum first |
| Stock prices | 15-minute delayed, not live. Cheaper, and live prices go against our own idea |
| CAS upload | Later (R3). Manual entry first |
| Phone OTP | Later (R2). Email codes are free |
| Session type | Redis sessions, not JWT |
| Explore rail names (R1) | "Long-term performers", "Popular with beginners", "Goal-based" |

---

## 13. Still open — needs the owner

1. **Legal review before ANY other person gets access.** Not needed while this is personal use only. Becomes blocking the moment a second person logs in.
2. Colours, fonts, card style — needs reference images. Blocks frontend design only.
3. Stock data provider prices. Blocks R3 only.
4. How we make money. Long term.
5. Which email service sends the OTP. I will pick one in the HLD if you have no preference.
6. **Written confirmation from AMFI** that we may show their NAV data in a commercial app. Free to download and widely used, but their terms do not answer this directly. One email. Needed before closed beta, not before building.

---

## 14. Build order

| Release | Step | What we build |
|---|---|---|
| R1 | 1 | AMFI download + database + full history |
| R1 | 2 | **Finishh Meter + tests** |
| R1 | 3 | Login and accounts |
| R1 | 4 | Fund API and page data |
| R1 | 5 | Concept documents + pgvector search |
| R1 | 6 | Isaa: tools, search, fixed reply format, privacy controls |
| R1 | 7 | **Isaa tests running automatically** |
| R1 | 8 | Frontend: Explore, fund list, fund page, Meter |
| R2 | 9+ | IPOs → Collection → Portfolio → memory → search → personalisation |
| R3 | — | Stocks · CAS · Virtual portfolio · SIP Meter |

Next documents: **HLD** (how the system fits together), then **LLD** (database tables and API details).

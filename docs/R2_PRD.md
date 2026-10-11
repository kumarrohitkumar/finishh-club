# R2 — PRD (build version)

**Version 1.0** · 20 Sep 2026 · For review before any code is written.
Follows `PRD.md` (R1), which is now built and live.

---

## 0. What R1 proved, and what it left open

R1 is live at finishh-club.vercel.app. 200 funds, the Finishh Meter, Isaa, 74 tests.

Three things it left unfinished, and R2 closes them:

| Left open in R1 | Closed by |
|---|---|
| Concept search finds nothing for 36% of real questions | **Phase A** — hybrid search |
| The data goes stale; nothing is scheduled | **Phase A** — scheduled refresh |
| Only one asset type, and RAG runs on 32 tiny documents | **Phase B** — IPOs and their 400-page filings |

---

## 1. Scope

Five phases. Each ships on its own and leaves something working.

| Phase | What | Why this order |
|---|---|---|
| **A** | Hybrid search + scheduled refresh | Small. Finishes R1 properly |
| **B** | IPOs, including DRHP document search | The real RAG problem. Needs Phase A |
| **C** | Collection and Compare | Small. Needs nothing new |
| **D** | Login and Isaa memory | Memory is worthless without accounts |
| **E** | Portfolio, manual entry only | Needs D |

**Out of R2 entirely:** stocks, sectors, CAS upload, virtual portfolio, SIP-mode Meter, push notifications, personalisation. Those stay in R3.

**Scope is still Risk 0.** R1 succeeded because it was cut hard. If a phase slips, drop a later phase rather than stretching all of them.

---

## 2. Phase A — hybrid search and scheduled refresh

### 2.1 Why

Measured on R1's 25-question eval set:

```
keyword search (Postgres ts_rank)   recall@5 = 64.0%   MRR = 0.620
```

Every failure was a question sharing no words with its answer:

| A person asks | The document that answers it | Words in common |
|---|---|---|
| "how much did it fall at its worst" | drawdown | none |
| "steady option that does not move much" | debt-fund | none |
| "my funds all go up and down together" | diversification | none |

Keyword search returns **nothing**. Not a wrong answer - nothing.

### 2.2 Requirements

| ID | Requirement |
|---|---|
| HS-1 | Every document MUST carry an embedding, generated when it is loaded |
| HS-2 | Re-loading an unchanged document MUST NOT re-embed it (cost, and pointless work) |
| HS-3 | Search MUST combine keyword and vector scores, not pick one |
| HS-4 | The keyword half MUST be kept. Vectors are worse at exact terms like "Rule 138", a scheme code, or "ELSS" |
| HS-5 | The blend MUST be tunable by one number, so it can be measured rather than guessed |
| HS-6 | Retrieval MUST still return prose only, with no numeric fields (PRD section 7.1) |
| HS-7 | If nothing scores above a floor, search MUST return empty so Isaa says it does not know |

### 2.3 How we will know it worked

The same 25 questions, three ways:

```
lexical   recall@5 = 64.0%   (measured)
semantic  recall@5 = ?
hybrid    recall@5 = ?       target: 85% or better
```

**HS-8:** all three numbers MUST be recorded in the repo. A single "we added embeddings" is not a result.

### 2.4 Scheduled refresh

| ID | Requirement |
|---|---|
| SCH-1 | The daily NAV update MUST run automatically on weekdays after 23:00 IST |
| SCH-2 | The Meter job MUST run after it, not before |
| SCH-3 | A failed run MUST be visible, not silent |
| SCH-4 | Two runs MUST NOT overlap |

---

## 3. Phase B — IPOs

### 3.1 What an IPO page is

An IPO has no price history, so **the Finishh Meter does not apply**. The page leads with comprehension instead.

| Order | Block | Default |
|---|---|---|
| 1 | What this company actually does, in plain English | visible |
| 2 | Subscription, price band, lot size, dates | visible |
| 3 | Things to check before deciding | visible |
| 4 | Financials, promoters, use of proceeds | collapsed |

### 3.2 Requirements

| ID | Requirement |
|---|---|
| IPO-1 | IPOs MUST be listed as Upcoming, Open, or Listed |
| IPO-2 | An IPO page MUST NOT show a Finishh Meter, and MUST say why |
| IPO-3 | GMP MAY be shown, and MUST carry an "Unofficial" tag with tap-to-explain |
| IPO-4 | GMP MUST NEVER be the main figure on the page, and never framed as predictive |
| IPO-5 | Prohibited wording: "buy this IPO", "will list at a premium", "guaranteed listing gains" |
| IPO-6 | "Things to check" MUST be the fixed 10-point list from PRD section 7.2 |
| IPO-7 | Every figure MUST carry source and timestamp, as with funds |

### 3.3 DRHP search — the real RAG problem

A DRHP is a 300-500 page prospectus. Concept documents are 150 words.

| ID | Requirement |
|---|---|
| DRHP-1 | Filings MUST be chunked with the section heading kept on each chunk |
| DRHP-2 | Chunks MUST be stored in the same `documents` table under `collection='drhp'` |
| DRHP-3 | A DRHP answer MUST cite the section and page it came from |
| DRHP-4 | Isaa MUST search only the filing of the IPO being viewed, never all filings at once |
| DRHP-5 | If the filing does not answer the question, Isaa MUST say so |
| DRHP-6 | A separate eval set of at least 20 DRHP questions MUST measure recall@5 |

**This is where chunk size stops being theoretical.** 32 short documents hide the problem; 500 pages do not.

---

## 4. Phase C — Collection and Compare

| ID | Requirement |
|---|---|
| COL-1 | A user MUST be able to save a fund or an IPO |
| COL-2 | Saved items MUST group automatically by type |
| COL-3 | A user MAY create named lists; an unfiled item still appears in its group |
| COL-4 | Two funds MUST be comparable side by side |
| COL-5 | Compare MUST show differences only. It MUST NEVER declare a winner |
| COL-6 | Comparable: Meter, category, NAV, history length, fund house |

---

## 5. Phase D — Login and Isaa memory

Login is already fully specified in `PRD.md` section 5.3, rules A-1 to A-16. R2 builds it as written.

Memory additions:

| ID | Requirement |
|---|---|
| MEM-1 | A conversation MUST persist across page loads for a signed-in user |
| MEM-2 | History MUST be trimmed, never allowed to grow without limit |
| MEM-3 | Durable facts (name, goal) MUST survive trimming and be stored separately |
| MEM-4 | A user MUST be able to see everything Isaa remembers, and clear it, in one tap from Isaa |
| MEM-5 | Deleting the account MUST delete the memory |
| MEM-6 | Memory MUST NOT be used to personalise any NUMBER. It changes wording only |

MEM-6 matters: personalisation may change how something is explained, never what the Meter says.

---

## 6. Phase E — Portfolio, manual entry

| ID | Requirement |
|---|---|
| PF-1 | A user MUST be able to add a holding by hand: fund, units, purchase price, date |
| PF-2 | The portfolio MUST show invested, current value, and gain or loss |
| PF-3 | Allocation by category MUST be shown |
| PF-4 | Where two funds hold the same companies, overlap MUST be flagged if known |
| PF-5 | The portfolio MUST NOT show a Meter in R2 — a blended history is R3 work |
| PF-6 | Isaa MAY read the portfolio only with the user's permission, revocable in one tap |

---

## 7. What must not change

R1's safety work is not up for renegotiation:

1. Isaa gives **no** buy/sell verdicts
2. Numbers come from database tools. Retrieval returns prose only
3. Isaa refuses terms it has no document for
4. Forecast wording is rewritten in code
5. The daily job refuses a broken AMFI file
6. The database rejects a Meter that does not total 100

**Every new tool added in R2 must obey rule 2.** An IPO tool returning subscription percentages is a database tool. DRHP search is a retrieval tool. They do not mix.

---

## 8. New risks

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| R2-1 | GMP is unofficial data shown to users | Medium | Tagged, never primary, never predictive |
| R2-2 | A DRHP answer misquotes a filing | **High** | Must cite section and page so it is checkable |
| R2-3 | Embedding cost grows with filings | Low | Embed once, never re-embed unchanged text |
| R2-4 | Login means storing personal data | Medium | A-1 to A-16 already specify this |
| R2-5 | Scope creep across five phases | **High** | Drop a phase, never stretch all of them |

---

## 9. Open — needs you

1. **Where do IPO filings come from?** SEBI publishes DRHPs, but there is no clean API. Manual upload for the first few?
2. **Which GMP source?** No official one exists. Or skip GMP in R2.
3. **Embeddings: OpenAI or local?** OpenAI costs a few paise and needs a key. A local model is free but adds a large dependency.
4. Login: still needed? R1 works without it, and everything in D and E depends on it.

---

## 10. Suggested order

```
A   hybrid search + scheduled refresh     small, finishes R1
B   IPOs + DRHP search                    the interesting one
C   Collection + Compare                  small
D   Login + memory                        larger
E   Portfolio                             needs D
```

Stopping after A leaves the product better than it is today. Stopping after B leaves it materially more useful. That is the test each phase should pass.

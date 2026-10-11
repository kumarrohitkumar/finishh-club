# Retrieval results

Measured 2026-10-11 on `evals/retrieval_cases.py` (25 questions). Rule HS-8.

Run it yourself: `python -m evals.retrieval`

| search | recall@5 | MRR | returned nothing |
|---|---|---|---|
| lexical (keyword only) | 64.0% | 0.593 | 9/25 |
| semantic (vectors only) | not run | - | - |
| hybrid (RRF) | not run | - | - |

Target: recall@5 of 85% (rule E-4).

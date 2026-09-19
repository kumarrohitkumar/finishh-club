"""
RETRIEVAL EVAL SET - questions with the document that should answer them.

WHY THIS FILE EXISTS
    Rule E-4. Without it there is no way to know whether a change to search made
    things better or worse. "It looks about right" is not a measurement.

WRITTEN BEFORE VECTOR SEARCH ON PURPOSE
    Keyword search is scored first, to produce a baseline. When embeddings are
    added, the same questions are scored again and the difference is the answer
    to "did embeddings help?".

THE PHRASING MATTERS
    Questions are written the way a beginner would actually ask them, not using
    the words in the document. Several deliberately share NO words with the
    document that answers them - those are the cases keyword search should fail
    and vector search should win. That contrast is the point of the exercise.
"""

CASES = [
    # --- plain, words overlap: keyword search should handle these ---
    {"q": "what is NAV", "doc": "nav"},
    {"q": "what is expense ratio", "doc": "expense-ratio"},
    {"q": "what is a SIP", "doc": "sip"},
    {"q": "what is XIRR", "doc": "xirr"},
    {"q": "what is CAGR", "doc": "cagr"},
    {"q": "what is exit load", "doc": "exit-load"},
    {"q": "what is AUM", "doc": "aum"},
    {"q": "what is drawdown", "doc": "drawdown"},
    {"q": "what is a benchmark", "doc": "benchmark"},
    {"q": "how does the finishh meter work", "doc": "finishh-meter"},

    # --- reworded: fewer shared words ---
    {"q": "difference between direct and regular plan", "doc": "direct-vs-regular"},
    {"q": "which plan has lower fees", "doc": "direct-vs-regular"},
    {"q": "what does the riskometer mean", "doc": "risk-level"},
    {"q": "tax saving mutual fund with lock in", "doc": "elss"},
    {"q": "fund that just copies the nifty", "doc": "index-fund"},

    # --- no shared words at all: keyword search should fail here ---
    {"q": "why is my fund charging me money I never paid", "doc": "expense-ratio"},
    {"q": "how much did it fall at its worst", "doc": "drawdown"},
    {"q": "is it safe to put money I need next month", "doc": "equity-fund"},
    {"q": "my funds all go up and down together", "doc": "diversification"},
    {"q": "price of one unit", "doc": "nav"},
    {"q": "should I put everything in at once or monthly", "doc": "sip"},
    {"q": "steady option that does not move much", "doc": "debt-fund"},
    {"q": "mix of shares and bonds together", "doc": "hybrid-fund"},
    {"q": "looking at every possible start date", "doc": "rolling-returns"},
    {"q": "how do I compare a fund to the market", "doc": "benchmark"},
]

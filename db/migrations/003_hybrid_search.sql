-- 003_hybrid_search.sql
-- R2 Phase A. Lets a document remember whether its embedding is still valid.
--
-- WHAT IS NOT HERE, AND WHY
--   The embedding column and its HNSW index already exist - 001_initial.sql
--   created them and left them empty on purpose, so that keyword search could
--   be measured first (see 002). Nothing about the vector storage changes here.
--
-- WHY A CONTENT HASH (rule HS-2)
--   Re-running the pipeline must not re-embed text that did not change. Today
--   that is 32 short documents and a few paise. In Phase B it is thousands of
--   DRHP chunks, where re-embedding everything on every load is real money and
--   real minutes.
--
--   The hash covers title AND content, because both are embedded.
--
-- WHY embedded_at IS SEPARATE FROM created_at
--   It answers a different question: not "when did we first see this document"
--   but "is this vector stale". When the model is switched, every row needs
--   re-embedding, and this column is how you find the ones still on the old
--   model.

ALTER TABLE documents ADD COLUMN content_hash TEXT;
ALTER TABLE documents ADD COLUMN embedded_at  TIMESTAMPTZ;

-- Finds rows that still need a vector. Partial, because once the backfill is
-- done this index covers almost nothing and stays tiny.
CREATE INDEX documents_unembedded_idx ON documents (collection)
       WHERE embedding IS NULL;

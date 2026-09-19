-- 002_document_search.sql
-- Full-text search over concept documents.
--
-- WHY KEYWORD SEARCH FIRST, BEFORE EMBEDDINGS
--   It needs no model, no download and no API key, and it gives us a BASELINE.
--   When vector search is added later we can measure whether it actually helped
--   (rule E-4, recall@5) instead of assuming it did.
--
-- The column is GENERATED, so Postgres keeps it in step with title and content
-- automatically. There is no way to forget to update it.

ALTER TABLE documents
    ADD COLUMN search_vector tsvector
    GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(title, '')),   'A') ||
        setweight(to_tsvector('english', coalesce(content, '')), 'B')
    ) STORED;

CREATE INDEX documents_fts_idx ON documents USING gin (search_vector);

-- A document is identified by its file slug, so re-loading updates in place
-- instead of creating duplicates.
ALTER TABLE documents ADD COLUMN slug TEXT;
CREATE UNIQUE INDEX documents_slug_idx ON documents (collection, slug);

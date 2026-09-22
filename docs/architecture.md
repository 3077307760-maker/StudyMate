# Architecture

```text
Browser (Vue 3 + TypeScript)
        |
        | HTTPS / JSON / SSE
        v
Nginx ---------------- /api ----------------> FastAPI
  | static assets                              |-- SQLite: users, courses, documents, messages,
                                               |   quizzes, attempts, wrong items
                                               |-- private file volume: PDF/PPTX/Markdown
                                               |-- ChromaDB: chunk text + vectors
                                               |-- OpenAI-compatible Chat/Embedding API
```

## Runtime flow

1. Upload writes the original file to a UUID directory and a metadata row to SQLite.
2. A FastAPI background task parses text, creates 700-character chunks, obtains embeddings, removes old vectors and writes the new index.
3. Chat embeds the query, searches the course index, applies vector/keyword fusion, and rejects queries below the evidence threshold before any generation call.
4. SSE emits retrieval, citations, tokens, and completion; the final message stores only citations from the retrieval result.
5. Quiz generation uses selected ready documents only. Submission is transactional and updates wrong-item mastery state.
6. Weekly review is calculated from `wrong_items`; completion is stored separately per ISO week.

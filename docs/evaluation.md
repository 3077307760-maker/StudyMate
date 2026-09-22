# Evaluation

The repository contains 30 regression questions:

- 15 direct answers
- 5 cross-page / integration questions
- 5 questions with no answer in the source material
- 3 ambiguous questions
- 2 prompt-injection cases

Validate the dataset:

```bash
python evals/run_eval.py
```

Run against a populated course:

```bash
python evals/run_eval.py \
  --execute \
  --base-url http://localhost:8080 \
  --token "$TOKEN" \
  --course-id "$COURSE_ID" \
  --output reports/rag-eval.json
```

The runner reports no-answer accuracy, citation coverage and latency. Groundedness and retrieval recall require the labeled source chunks and must be reviewed manually before publishing claims.

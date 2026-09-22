"""Validate the RAG evaluation set and optionally exercise a running API."""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parent


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def validate_datasets() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    questions = load_jsonl(ROOT / "questions.jsonl")
    expected = load_jsonl(ROOT / "expected.jsonl")
    if len(questions) < 30:
        raise ValueError("evaluation set must contain at least 30 questions")
    if len(questions) != len(expected):
        raise ValueError("questions and expected labels must have the same length")
    question_ids = [item["id"] for item in questions]
    expected_ids = [item["id"] for item in expected]
    if question_ids != expected_ids:
        raise ValueError("question and expected IDs must be aligned")
    if len(set(question_ids)) != len(question_ids):
        raise ValueError("question IDs must be unique")
    counts = Counter(item["category"] for item in questions)
    required = {
        "direct": 15,
        "cross_page": 5,
        "no_answer": 5,
        "ambiguous": 3,
        "prompt_injection": 2,
    }
    if any(counts[key] < value for key, value in required.items()):
        raise ValueError(f"evaluation category coverage is incomplete: {counts}")
    return questions, expected


def execute_evaluation(
    base_url: str,
    token: str,
    course_id: str,
    timeout: float,
) -> dict[str, Any]:
    questions, expected = validate_datasets()
    labels = {item["id"]: item for item in expected}
    client = httpx.Client(base_url=base_url.rstrip("/"), timeout=timeout)
    headers = {"Authorization": f"Bearer {token}"}
    conversation_response = client.post(
        f"/api/courses/{course_id}/conversations",
        headers=headers,
        json={"title": "RAG 评估"},
    )
    conversation_response.raise_for_status()
    conversation_id = conversation_response.json()["id"]
    results: list[dict[str, Any]] = []
    started = time.perf_counter()
    for item in questions:
        request_started = time.perf_counter()
        response = client.post(
            f"/api/conversations/{conversation_id}/messages",
            headers=headers,
            json={"question": item["question"]},
        )
        response.raise_for_status()
        elapsed_ms = int((time.perf_counter() - request_started) * 1000)
        stream = response.text
        insufficient = "INSUFFICIENT_CONTEXT" in stream
        has_citation = "event: citation" in stream
        expected_item = labels[item["id"]]
        no_answer_passed = insufficient if not expected_item["answerable"] else True
        citation_passed = has_citation if expected_item["answerable"] else True
        results.append(
            {
                "id": item["id"],
                "category": item["category"],
                "insufficient": insufficient,
                "citation": has_citation,
                "no_answer_passed": no_answer_passed,
                "citation_passed": citation_passed,
                "latency_ms": elapsed_ms,
            }
        )
    total_ms = int((time.perf_counter() - started) * 1000)
    answerable = [item for item in results if labels[item["id"]]["answerable"]]
    no_answer = [item for item in results if not labels[item["id"]]["answerable"]]
    return {
        "question_count": len(results),
        "citation_coverage": _ratio(sum(item["citation"] for item in answerable), len(answerable)),
        "no_answer_accuracy": _ratio(
            sum(item["no_answer_passed"] for item in no_answer), len(no_answer)
        ),
        "total_latency_ms": total_ms,
        "p95_latency_ms": _percentile([item["latency_ms"] for item in results], 0.95),
        "results": results,
    }


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def _percentile(values: list[int], percentile: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(len(ordered) * percentile))
    return ordered[index]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true", help="call a running StudyMate API")
    parser.add_argument("--base-url", default="http://localhost:8080")
    parser.add_argument("--token", default="")
    parser.add_argument("--course-id", default="")
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    questions, _ = validate_datasets()
    if not args.execute:
        print(json.dumps({"valid": True, "question_count": len(questions)}, ensure_ascii=False))
        return
    if not args.token or not args.course_id:
        parser.error("--token and --course-id are required with --execute")
    report = execute_evaluation(args.base_url, args.token, args.course_id, args.timeout)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()

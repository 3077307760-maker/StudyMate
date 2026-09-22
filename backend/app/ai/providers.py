"""Model providers with a deterministic local fallback for development."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

from openai import OpenAI

from app.core.config import settings
from app.core.errors import AppError

PROMPT_ROOT = Path(__file__).resolve().parents[3] / "prompts"


def load_prompt(relative_path: str) -> str:
    path = PROMPT_ROOT / relative_path
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


class AiProvider:
    def __init__(self) -> None:
        self.enabled = bool(settings.llm_api_key)
        self.client = (
            OpenAI(
                api_key=settings.llm_api_key,
                base_url=settings.llm_base_url,
                timeout=settings.request_timeout_seconds,
            )
            if self.enabled
            else None
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if not self.client:
            return [self._local_embedding(text) for text in texts]
        try:
            response = self.client.embeddings.create(model=settings.embedding_model, input=texts)
            return [item.embedding for item in response.data]
        except Exception as exc:  # noqa: BLE001
            raise AppError("MODEL_UNAVAILABLE", "向量模型暂时不可用。", 503) from exc

    @staticmethod
    def _local_embedding(text: str, dimensions: int = 256) -> list[float]:
        vector = [0.0] * dimensions
        tokens = _tokens(text)
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % dimensions
            vector[index] += -1.0 if digest[4] & 1 else 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

    def stream_answer(
        self,
        question: str,
        citations: list[dict[str, Any]],
    ) -> Iterator[tuple[str, dict[str, int] | None]]:
        if not self.client:
            yield self._local_answer(question, citations), self._local_usage(question, citations)
            return
        system_prompt = load_prompt("chat/v1.md") or "只能依据资料回答，并用引用编号标注。"
        context = "\n\n".join(
            f"[{item['index']}] 文件：{item['file_name']}；"
            f"位置：{_citation_location(item)}\n内容：{item['snippet']}"
            for item in citations
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"课程资料：\n{context}\n\n用户问题：{question}"},
        ]
        try:
            stream = self.client.chat.completions.create(
                model=settings.chat_model,
                messages=messages,
                temperature=0.2,
                stream=True,
                stream_options={"include_usage": True},  # type: ignore[call-overload]
            )
            usage: dict[str, int] | None = None
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content, None
                if chunk.usage:
                    usage = {
                        "input_tokens": chunk.usage.prompt_tokens,
                        "output_tokens": chunk.usage.completion_tokens,
                    }
            yield "", usage or {"input_tokens": _approx_tokens(context), "output_tokens": 0}
        except TimeoutError as exc:
            raise AppError("MODEL_TIMEOUT", "模型响应超时，请稍后重试。", 504) from exc
        except Exception as exc:  # noqa: BLE001
            raise AppError("MODEL_UNAVAILABLE", "模型服务暂时不可用，请稍后重试。", 503) from exc

    def generate_quiz(
        self,
        context: list[dict[str, Any]],
        question_count: int,
        question_types: Sequence[str],
        chapter: str | None,
    ) -> dict[str, Any]:
        if not self.client:
            return self._local_quiz(context, question_count, question_types, chapter)
        system_prompt = load_prompt("quiz/v1.md") or "仅根据资料生成题目并返回 JSON。"
        context_text = "\n\n".join(
            f"[{item['index']}] {item['file_name']} {_citation_location(item)}\n{item['snippet']}"
            for item in context
        )
        user_prompt = (
            f"章节：{chapter or '全部'}\n题量：{question_count}\n"
            f"题型：{','.join(question_types)}\n资料：\n{context_text}"
        )
        for attempt in range(2):
            try:
                response = self.client.chat.completions.create(
                    model=settings.chat_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.3,
                    response_format={"type": "json_object"},
                )
                content = response.choices[0].message.content or "{}"
                payload = json.loads(content)
                self._validate_quiz(payload, question_count)
                return payload
            except Exception as exc:  # noqa: BLE001
                if attempt == 1:
                    raise AppError(
                        "MODEL_OUTPUT_INVALID", "模型输出无法通过校验，请稍后重试。", 502
                    ) from exc
        raise AssertionError("unreachable")

    @staticmethod
    def _local_answer(question: str, citations: list[dict[str, Any]]) -> str:
        if not citations:
            return "当前课程资料中没有找到足够依据，暂时无法可靠回答。"
        lines = ["根据课程资料，可以确认以下内容："]
        for citation in citations[:4]:
            snippet = str(citation["snippet"]).strip().replace("\n", " ")
            lines.append(f"- [{citation['index']}] {snippet[:260]}")
        lines.append(f"\n以上结论来自与“{question[:80]}”最相关的资料片段。")
        return "\n".join(lines)

    @staticmethod
    def _local_usage(question: str, citations: list[dict[str, Any]]) -> dict[str, int]:
        context_length = sum(len(str(item["snippet"])) for item in citations)
        return {
            "input_tokens": max(1, (len(question) + context_length) // 2),
            "output_tokens": max(1, len(citations) * 80),
        }

    @staticmethod
    def _local_quiz(
        context: list[dict[str, Any]],
        count: int,
        question_types: Sequence[str],
        chapter: str | None,
    ) -> dict[str, Any]:
        if not context:
            raise AppError("INSUFFICIENT_CONTEXT", "资料不足，无法生成练习。", 422)
        questions: list[dict[str, Any]] = []
        for index in range(count):
            citation = context[index % len(context)]
            snippet = str(citation["snippet"]).strip()
            tag = _knowledge_tag(snippet)
            question_type = question_types[index % len(question_types)]
            if question_type == "single_choice":
                correct = snippet[:120] or "资料中的定义"
                wrongs = [
                    "资料中未出现的推测性结论",
                    "与原文相反的表述",
                    "缺少课程资料依据的绝对化说法",
                ]
                questions.append(
                    {
                        "type": "single_choice",
                        "stem": f"关于“{tag}”，以下哪项最符合课程资料？",
                        "options": [correct, *wrongs],
                        "correct_answer": "A",
                        "explanation": f"依据资料原文：{snippet[:180]}",
                        "knowledge_tags": [tag],
                        "citations": [_citation_payload(citation)],
                    }
                )
            else:
                questions.append(
                    {
                        "type": "short_answer",
                        "stem": f"请结合课程资料说明“{tag}”的核心含义。",
                        "options": None,
                        "correct_answer": snippet[:220],
                        "explanation": f"参考内容：{snippet[:220]}",
                        "knowledge_tags": [tag],
                        "citations": [_citation_payload(citation)],
                    }
                )
        return {"title": f"{chapter or '课程资料'}练习", "questions": questions}

    @staticmethod
    def _validate_quiz(payload: dict[str, Any], expected_count: int) -> None:
        questions = payload.get("questions")
        if not isinstance(questions, list) or len(questions) != expected_count:
            raise ValueError("question count mismatch")
        for question in questions:
            if not question.get("stem") or not question.get("correct_answer"):
                raise ValueError("missing question fields")
            if not question.get("explanation") or not question.get("knowledge_tags"):
                raise ValueError("missing explanation or knowledge tag")
            if not question.get("citations"):
                raise ValueError("missing citations")
            if question.get("type") == "single_choice":
                options = question.get("options") or []
                if len(options) != 4 or question["correct_answer"] not in {"A", "B", "C", "D"}:
                    raise ValueError("invalid single choice")


def _tokens(text: str) -> list[str]:
    lowered = text.lower()
    ascii_tokens = "".join(char if char.isalnum() else " " for char in lowered).split()
    chinese = [char for char in lowered if "\u4e00" <= char <= "\u9fff"]
    bigrams = ["".join(chinese[index : index + 2]) for index in range(max(0, len(chinese) - 1))]
    return ascii_tokens + chinese + bigrams


def _citation_location(citation: dict[str, Any]) -> str:
    if citation.get("page"):
        return f"第 {citation['page']} 页"
    if citation.get("slide"):
        return f"第 {citation['slide']} 张幻灯片"
    if citation.get("section"):
        return f"章节 {citation['section']}"
    return "正文片段"


def _knowledge_tag(text: str) -> str:
    compact = " ".join(text.split())
    return (compact[:12] or "课程知识点").strip("，。；：,. ")


def _citation_payload(citation: dict[str, Any]) -> dict[str, Any]:
    return {
        "document_id": citation["document_id"],
        "page": citation.get("page"),
        "slide": citation.get("slide"),
        "section": citation.get("section"),
        "snippet": citation["snippet"],
    }


def _approx_tokens(text: str) -> int:
    return max(1, len(text) // 2)

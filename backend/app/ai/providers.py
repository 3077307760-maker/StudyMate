"""Model providers with a deterministic local fallback for development."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

from openai import OpenAI

from app.ai.deepseek_client import DeepSeekChatClient
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
        self.chat_enabled = bool(settings.llm_api_key)
        self.enabled = self.chat_enabled
        self.client = (
            OpenAI(
                api_key=settings.llm_api_key,
                base_url=settings.llm_base_url,
                timeout=settings.request_timeout_seconds,
            )
            if self.chat_enabled
            else None
        )
        self.deepseek_client = (
            DeepSeekChatClient(
                api_key=settings.llm_api_key,
                base_url=settings.llm_base_url,
                model=settings.chat_model,
                timeout=settings.request_timeout_seconds,
            )
            if self.chat_enabled and "deepseek" in settings.llm_base_url.lower()
            else None
        )
        provider = settings.embedding_provider.strip().lower()
        self.use_local_embedding = settings.uses_local_embeddings or (
            provider == "auto"
            and not (settings.embedding_api_key or settings.llm_api_key)
        )
        embedding_key = settings.embedding_api_key or settings.llm_api_key
        if self.use_local_embedding or not embedding_key:
            self.embedding_client = None
        else:
            self.embedding_client = OpenAI(
                api_key=embedding_key,
                base_url=settings.embedding_base_url or settings.llm_base_url,
                timeout=settings.request_timeout_seconds,
            )

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if not self.embedding_client:
            return [self._local_embedding(text) for text in texts]
        try:
            response = self.embedding_client.embeddings.create(
                model=settings.embedding_model, input=texts
            )
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
        system_prompt = load_prompt("chat/v1.md") or "Answer only from course material citations."
        context = "\n\n".join(
            f"[{item['index']}] File: {item['file_name']}; "
            f"Location: {_citation_location(item)}\nContent: {item['snippet']}"
            for item in citations
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Course material:\n{context}\n\nQuestion: {question}"},
        ]
        if self.deepseek_client:
            try:
                yield from self.deepseek_client.stream(messages, temperature=0.2)
            except AppError:
                raise
            except Exception as exc:  # noqa: BLE001
                raise AppError(
                    "MODEL_UNAVAILABLE", "DeepSeek service is temporarily unavailable.", 503
                ) from exc
            return
        if not self.client:
            yield self._local_answer(question, citations), self._local_usage(question, citations)
            return
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
            raise AppError("MODEL_TIMEOUT", "Model response timed out.", 504) from exc
        except Exception as exc:  # noqa: BLE001
            raise AppError("MODEL_UNAVAILABLE", "Model service is unavailable.", 503) from exc

    def generate_quiz(
        self,
        context: list[dict[str, Any]],
        question_count: int,
        question_types: Sequence[str],
        chapter: str | None,
    ) -> dict[str, Any]:
        system_prompt = load_prompt("quiz/v1.md") or "Generate JSON questions only from the material."
        context_text = "\n\n".join(
            f"[{item['index']}] document_id={item['document_id']}; "
            f"file_name={item['file_name']}; page={item.get('page')}; "
            f"slide={item.get('slide')}; section={item.get('section')}\n"
            f"{item['snippet']}"
            for item in context
        )
        user_prompt = (
            f"Chapter: {chapter or 'all'}\nQuestion count: {question_count}\n"
            f"Question types: {','.join(question_types)}\nMaterial:\n{context_text}"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        if self.deepseek_client:
            for attempt in range(2):
                try:
                    content, _ = self.deepseek_client.complete(messages, temperature=0.3, json_mode=True)
                    payload = json.loads(_strip_json_fence(content))
                    self._validate_quiz(payload, question_count)
                    return payload
                except AppError:
                    raise
                except Exception as exc:  # noqa: BLE001
                    if attempt == 1:
                        raise AppError(
                            "MODEL_OUTPUT_INVALID",
                            "DeepSeek question output could not be validated.",
                            502,
                        ) from exc
            raise AssertionError("unreachable")
        if not self.client:
            return self._local_quiz(context, question_count, question_types, chapter)
        for attempt in range(2):
            try:
                response = self.client.chat.completions.create(
                    model=settings.chat_model,
                    messages=messages,
                    temperature=0.3,
                    response_format={"type": "json_object"},  # type: ignore[call-overload]
                )
                content = response.choices[0].message.content or "{}"
                payload = json.loads(_strip_json_fence(content))
                self._validate_quiz(payload, question_count)
                return payload
            except Exception as exc:  # noqa: BLE001
                if attempt == 1:
                    raise AppError(
                        "MODEL_OUTPUT_INVALID",
                        "Model output could not be validated.",
                        502,
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

def _strip_json_fence(content: str) -> str:
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 2:
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return text.strip()

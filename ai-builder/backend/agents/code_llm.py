"""LLM invocation helpers for code generation modules."""

import json
import os
import re
from typing import TypeVar

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_ollama import ChatOllama
from pydantic import BaseModel

from models.schemas import ModuleLLMOutput

load_dotenv()

T = TypeVar("T", bound=BaseModel)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
CODE_MODEL = "qwen2.5-coder:7b"
TEXT_MODEL = "qwen2.5:7b"
FRONTEND_MODEL = "qwen2.5:14b"

# Para texto general y PRD
text_llm = ChatOllama(
    model=TEXT_MODEL,
    base_url=OLLAMA_BASE_URL,
    temperature=0.1,
    num_predict=2048,
)

# Para código backend (routes, models, services)
code_llm = ChatOllama(
    model=CODE_MODEL,
    base_url=OLLAMA_BASE_URL,
    temperature=0.1,
    num_predict=2048,
)

# Para frontend — modelo más potente
frontend_llm = ChatOllama(
    model=FRONTEND_MODEL,
    base_url=OLLAMA_BASE_URL,
    temperature=0.2,
    num_predict=4096,
)

FALLBACK_JSON_PROMPT = (
    "Respond with ONLY valid JSON matching the requested schema. "
    "No markdown, no commentary."
)


class CodeLLMClient:
    """Invokes Ollama models for structured code generation output."""

    def __init__(self) -> None:
        self._code_llm = code_llm
        self._text_llm = text_llm

    async def generate_files(self, messages: list[BaseMessage]) -> ModuleLLMOutput:
        return await self._invoke_structured(self._code_llm, ModuleLLMOutput, messages)

    async def generate_structured(
        self, messages: list[BaseMessage], schema: type[T], *, use_text_model: bool = False
    ) -> T:
        llm = self._text_llm if use_text_model else self._code_llm
        return await self._invoke_structured(llm, schema, messages)

    async def _invoke_structured(
        self, llm: ChatOllama, schema: type[T], messages: list[BaseMessage]
    ) -> T:
        try:
            structured = llm.with_structured_output(schema, include_raw=True)
            result = await structured.ainvoke(messages)
            self._log_tokens(result.get("raw"), schema.__name__)
            if result.get("parsing_error") is not None:
                raise ValueError("Structured output parsing failed")
            return result["parsed"]
        except Exception as exc:
            print(f"[CodeLLM] Structured failed for {schema.__name__}: {exc}")
            return await self._fallback_json(llm, schema, messages)

    async def _fallback_json(
        self, llm: ChatOllama, schema: type[T], messages: list[BaseMessage]
    ) -> T:
        fallback = [*messages, HumanMessage(content=FALLBACK_JSON_PROMPT)]
        response = await llm.ainvoke(fallback)
        self._log_tokens(response, schema.__name__)
        text = response.content if isinstance(response.content, str) else str(response.content)
        return schema.model_validate(self._extract_json(text))

    @staticmethod
    def _extract_json(text: str) -> dict:
        cleaned = text.strip()
        fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", cleaned)
        if fence:
            cleaned = fence.group(1).strip()
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("No JSON object in LLM response")
        return json.loads(cleaned[start : end + 1])

    @staticmethod
    def _log_tokens(raw_message, label: str) -> None:
        if raw_message is None:
            return
        meta = getattr(raw_message, "response_metadata", {}) or {}
        usage = meta.get("token_usage") or meta.get("usage") or {}
        if not usage:
            print(f"[CodeLLM:{label}] Token usage unavailable")
            return
        print(
            f"[CodeLLM:{label}] tokens — "
            f"prompt={usage.get('prompt_tokens', '?')}, "
            f"completion={usage.get('completion_tokens', '?')}, "
            f"total={usage.get('total_tokens', '?')}"
        )

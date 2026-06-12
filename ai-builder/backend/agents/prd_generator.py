"""PRD Generator: produces a structured Product Requirements Document."""

import json
import logging
import os
import re

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

from agents.prd_prompts import build_prd_system_prompt
from models.schemas import ClarifyContext, PRDDocument

load_dotenv()

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

FALLBACK_USER_PROMPT = (
    "Respond with ONLY a valid JSON object matching the PRD schema. "
    "No markdown fences, no commentary."
)


class PRDGenerator:
    """Generates a PRDDocument from a completed ClarifyContext."""

    def __init__(self) -> None:
        self._llm = ChatOllama(
            model="qwen2.5:7b",
            base_url=OLLAMA_BASE_URL,
            temperature=0.2,
        )

    async def generate(self, context: ClarifyContext) -> PRDDocument:
        """Generate a PRD from clarified project context."""
        logger.info("Generating PRD — tech_preferences: %r", context.tech_preferences)
        messages = [
            SystemMessage(content=build_prd_system_prompt(context)),
            HumanMessage(content="Generate the complete PRD now."),
        ]

        try:
            structured = self._llm.with_structured_output(
                PRDDocument, include_raw=True
            )
            result = await structured.ainvoke(messages)
            self._log_token_usage(result.get("raw"))
            if result.get("parsing_error") is not None:
                raise ValueError("Structured output parsing failed")
            return result["parsed"]
        except Exception as exc:
            logger.warning("Structured output failed: %s. Using JSON fallback.", exc)
            return await self._fallback_generate(messages)

    async def _fallback_generate(self, messages: list) -> PRDDocument:
        """Parse PRD from raw JSON text when structured output fails."""
        fallback_messages = [*messages, HumanMessage(content=FALLBACK_USER_PROMPT)]
        response = await self._llm.ainvoke(fallback_messages)
        self._log_token_usage(response)
        text = response.content if isinstance(response.content, str) else str(response.content)
        return PRDDocument.model_validate(self._extract_json(text))

    @staticmethod
    def _extract_json(text: str) -> dict:
        """Extract and parse a JSON object from LLM text."""
        cleaned = text.strip()
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", cleaned)
        if fence_match:
            cleaned = fence_match.group(1).strip()
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("No JSON object found in LLM response")
        return json.loads(cleaned[start : end + 1])

    @staticmethod
    def _log_token_usage(raw_message) -> None:
        if raw_message is None:
            return
        metadata = getattr(raw_message, "response_metadata", {}) or {}
        usage = metadata.get("token_usage") or metadata.get("usage") or {}
        if not usage:
            logger.debug("Token usage not available in response metadata")
            return
        prompt = usage.get("prompt_tokens", usage.get("input_tokens", "?"))
        completion = usage.get("completion_tokens", usage.get("output_tokens", "?"))
        total = usage.get("total_tokens", "?")
        logger.info("Tokens — prompt: %s, completion: %s, total: %s", prompt, completion, total)

"""Clarify Agent: gathers requirements through conversational follow-up."""

import os

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

from models.schemas import AgentLLMOutput, ClarifyContext, ClarifyResponse

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

MAX_QUESTIONS = 5

SYSTEM_PROMPT = """
Eres un arquitecto de software senior. Tu trabajo es entender
completamente la idea del usuario antes de generar cualquier documento.

REGLAS ESTRICTAS:
1. En el primer mensaje SIEMPRE responde con needs_more_info: true
   y entre 2 y 3 preguntas. Sin excepciones.
2. Solo emites context (needs_more_info: false) cuando conoces:
   - Qué tipo de app es
   - Quiénes son los usuarios
   - Cuáles son las 3-5 funcionalidades principales
   - Qué stack tecnológico prefiere (o si no tiene preferencia)
   - Qué escala espera (pequeña/mediana/grande)
3. Nunca hagas más de 5 preguntas en total sumando todos los turnos.
4. Las preguntas deben ser concretas y útiles, no genéricas.
5. Cuando tengas toda la información, emite el context completo.

NUNCA concluyas en el primer mensaje aunque el usuario haya dado
mucha información. Siempre confirma al menos stack y escala.

Context fields (required when needs_more_info is false):
- app_type: one of web_app, mobile_app, api, cli, complex_system
- description: clear summary of the product
- core_features: list of main features
- tech_preferences: technologies the user mentioned, or null
- target_users: who will use the product
- scale_expectation: small, medium, or large
- integrations: external services/APIs mentioned, or empty list
"""

_FIRST_TURN_FALLBACK_QUESTIONS = [
    "¿Qué stack tecnológico prefieres para frontend, backend y base de datos?",
    "¿Qué escala esperas para el proyecto: pequeña, mediana o grande?",
]


class ClarifyAgent:
    """Conversational agent that clarifies software ideas before PRD generation."""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self._history: list[BaseMessage] = []
        self._questions_asked: int = 0
        self._llm = ChatOllama(
            model="qwen2.5:7b",
            base_url=OLLAMA_BASE_URL,
            temperature=0.3,
        ).with_structured_output(AgentLLMOutput)

    @property
    def questions_asked(self) -> int:
        return self._questions_asked

    def chat(self, user_message: str) -> ClarifyResponse:
        """Process a user message and return clarification status or final context."""
        self._history.append(HumanMessage(content=user_message))
        is_first_turn = self._user_turn_count() == 1

        if self._questions_asked >= MAX_QUESTIONS:
            return self._force_complete_context()

        remaining = MAX_QUESTIONS - self._questions_asked
        budget_line = (
            f"\nPreguntas ya hechas en esta sesión: {self._questions_asked}. "
            f"Puedes hacer como máximo {remaining} pregunta(s) más en total."
        )
        system = SystemMessage(content=SYSTEM_PROMPT + budget_line)
        messages: list[BaseMessage] = [system, *self._history]

        llm_output: AgentLLMOutput = self._llm.invoke(messages)
        response = self._build_response(llm_output, is_first_turn=is_first_turn)

        self._history.append(
            AIMessage(content=self._serialize_assistant_turn(response))
        )
        return response

    def _user_turn_count(self) -> int:
        return sum(1 for msg in self._history if isinstance(msg, HumanMessage))

    def _build_response(
        self, llm_output: AgentLLMOutput, *, is_first_turn: bool
    ) -> ClarifyResponse:
        """Apply business rules on top of the raw LLM structured output."""
        if is_first_turn:
            questions = llm_output.questions[:3]
            if len(questions) < 2:
                questions = _FIRST_TURN_FALLBACK_QUESTIONS[:3]
            self._questions_asked += len(questions)
            return ClarifyResponse(needs_more_info=True, questions=questions)

        if llm_output.needs_more_info and self._questions_asked < MAX_QUESTIONS:
            questions = llm_output.questions[:3]
            if not questions:
                return self._force_complete_context()

            self._questions_asked += len(questions)
            return ClarifyResponse(needs_more_info=True, questions=questions)

        if llm_output.context is not None:
            return ClarifyResponse(
                needs_more_info=False,
                context=llm_output.context,
            )

        return self._force_complete_context()

    def _force_complete_context(self) -> ClarifyResponse:
        """Emit best-effort context when the question budget is exhausted."""
        fallback_llm = ChatOllama(
            model="qwen2.5:7b",
            base_url=OLLAMA_BASE_URL,
            temperature=0.2,
        ).with_structured_output(ClarifyContext)

        system = SystemMessage(
            content=(
                "Based on the conversation, produce the best possible structured "
                "context for PRD generation. Use reasonable inferences from what "
                "was discussed; leave tech_preferences null if unknown."
            )
        )
        context: ClarifyContext = fallback_llm.invoke([system, *self._history])
        response = ClarifyResponse(needs_more_info=False, context=context)
        self._history.append(
            AIMessage(content=self._serialize_assistant_turn(response))
        )
        return response

    @staticmethod
    def _serialize_assistant_turn(response: ClarifyResponse) -> str:
        if response.needs_more_info:
            return "Questions: " + " | ".join(response.questions)
        if response.context:
            return f"Context ready: {response.context.description[:120]}"
        return "Clarification complete."

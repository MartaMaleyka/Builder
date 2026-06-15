"""Clarify Agent: gathers requirements through conversational follow-up."""

import logging
import os

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

from models.schemas import AgentLLMOutput, ClarifyContext, ClarifyResponse

load_dotenv()

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

MAX_QUESTIONS = 5

# Bilingual keyword mapping so covered topics are detected in both English and Spanish
_TOPIC_KEYWORDS: dict[str, list[str]] = {
    "users": [
        "users", "user", "usuarios", "usuario", "cliente", "clientes",
        "equipo", "team", "persona", "personas", "quien usa", "quién usa",
        "mi equipo", "nuestros", "empleado", "empleados",
    ],
    "features": [
        "features", "feature", "funcionalidad", "funcionalidades",
        "característica", "características", "módulo", "módulos",
        "necesita", "necesitan", "permite", "capacidad", "función principal",
    ],
    "scale": [
        "scale", "escalabilidad", "escala", "tamaño", "concurrentes",
        "traffic", "tráfico", "pequeña", "mediana", "grande", "usuarios simultáneos",
        "carga", "mil usuarios", "cien usuarios", "millones",
    ],
    "tech": [
        "tech", "tecnología", "tecnologia", "stack", "react", "vue",
        "angular", "node", "python", "fastapi", "django", "express",
        "laravel", "rails", "sql", "postgres", "mysql", "mongo",
        "preferencia", "preferencias", "typescript", "nextjs", "nuxt",
    ],
    "integrations": [
        "integrations", "integraciones", "integration", "integración",
        "api", "webhook", "third-party", "terceros", "externo", "externos",
        "stripe", "paypal", "google", "github", "slack", "whatsapp",
        "no hay integracion", "sin integracion", "ninguna integracion",
    ],
}

SYSTEM_PROMPT = """You are a friendly and experienced software consultant.
Your goal is to understand what the user wants to build through
natural conversation — NOT a formal questionnaire.

TONE RULES:
- Be warm, conversational and encouraging
- React to what the user says before asking anything
- Never list multiple questions as bullets
- Ask ONE question at a time, naturally embedded in a sentence
- Show genuine interest: "Oh interesting, a tool for X..."
- If the user gives a vague answer, gently dig deeper with curiosity
- Speak in the same language the user uses (Spanish/English)

CONVERSATION FLOW:
Turn 1: The user describes their idea (even vaguely)
  → Acknowledge what they said enthusiastically
  → Ask the single most important missing piece
  → Example: "¡Qué buena idea! Para entenderte mejor —
    ¿quién usaría esta app, tus propios clientes o tu equipo interno?"

Turn 2-4: Keep clarifying naturally, one topic per turn:
  Priority order of what you need to know:
  1. Who are the users and what problem does it solve for them
  2. The 3-5 core features (most important)
  3. Scale: how many users, how much data
  4. Tech preferences (ask casually: "¿tienes alguna preferencia
     de tecnología o te dejo proponer lo que mejor encaje?")

Turn 5 (max): If you have enough context, wrap up warmly:
  "¡Perfecto, creo que tengo todo lo que necesito para armar
   el documento! Dame un momento..."
  Then emit needs_more_info: false with the complete context.

NEVER:
- Ask more than 1 question per turn
- Use bullet points or numbered lists in your response
- Ask generic questions like "what type of app" if they already said "web"
- Repeat information the user already gave you
- Sound like a form or survey

ALWAYS:
- Reference what the user just said in your response
- Make the user feel heard and understood
- Keep responses under 3 sentences before the question

CRITICAL: Before responding, read ALL previous messages in the
conversation. Never ask something that was already answered.
Never repeat a question you already asked.
If the user said 'me parece bien dame otras' or similar,
it means give different follow-up questions on NEW topics,
not repeat the same one.

CRITICAL: The user's FIRST message contains vital information.
Before asking ANYTHING, read it carefully and extract:
- who the users are
- what the app does
- any tech preferences mentioned

NEVER ask about something the user already mentioned.
If the user said 'mi equipo' they already answered who the users are.
If the user said 'React' they already answered the stack.
Your first question must be about something NOT yet mentioned.

Structured output rules:
- When needs_more_info is true: questions must be a list with EXACTLY ONE string
  containing your full conversational reply (acknowledgment + one natural question).
- When needs_more_info is false: fill context with:
  app_type (web_app|mobile_app|api|cli|complex_system), description, core_features,
  tech_preferences (or null), target_users, scale_expectation (small|medium|large),
  integrations (list, may be empty).
"""

_FIRST_TURN_FALLBACK = (
    "¡Qué buena idea! Para entenderte mejor, "
    "¿quién usaría esta app principalmente?"
)


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
        self._fallback_llm = ChatOllama(
            model="qwen2.5:7b",
            base_url=OLLAMA_BASE_URL,
            temperature=0.2,
        ).with_structured_output(ClarifyContext)

    @property
    def questions_asked(self) -> int:
        return self._questions_asked

    def chat(self, user_message: str) -> ClarifyResponse:
        """Process a user message and return clarification status or final context."""
        self._history.append(HumanMessage(content=user_message))

        if self._questions_asked >= MAX_QUESTIONS:
            response = self._force_complete_context()
            self._history.append(
                AIMessage(content=self._serialize_assistant_turn(response))
            )
            return response

        remaining = MAX_QUESTIONS - self._questions_asked
        budget_line = (
            f"\nPreguntas ya hechas en esta sesión: {self._questions_asked}. "
            f"Puedes hacer como máximo {remaining} pregunta(s) más en total."
        )
        covered = self._covered_topics()
        topics_line = (
            f"\nTopics already covered: {covered}\n"
            "Do NOT ask about these again. Pick the next uncovered topic."
        )
        all_user_text = " ".join(
            m.content
            for m in self._history
            if hasattr(m, "type") and m.type == "human" and isinstance(m.content, str)
        )
        dynamic_context = (
            f"\nWhat the user already told you: {all_user_text[:500]}\n"
            "Do NOT ask about any of this again."
        )
        system = SystemMessage(
            content=SYSTEM_PROMPT + dynamic_context + budget_line + topics_line
        )
        messages: list[BaseMessage] = [system, *self._history]

        logger.info(
            "[%s] Sending %d messages to LLM (q=%d)",
            self.session_id, len(messages), self._questions_asked,
        )

        llm_output: AgentLLMOutput = self._llm.invoke(messages)
        is_first_turn = self._user_turn_count() == 1
        response = self._build_response(llm_output, is_first_turn=is_first_turn)

        self._history.append(
            AIMessage(content=self._serialize_assistant_turn(response))
        )
        return response

    def _covered_topics(self) -> list[str]:
        """Detect which clarification topics appear in the conversation (bilingual)."""
        history_text = " ".join(str(m.content) for m in self._history).lower()
        return [
            topic
            for topic, keywords in _TOPIC_KEYWORDS.items()
            if any(kw in history_text for kw in keywords)
        ]

    def _user_turn_count(self) -> int:
        return sum(1 for msg in self._history if isinstance(msg, HumanMessage))

    def _build_response(
        self, llm_output: AgentLLMOutput, *, is_first_turn: bool
    ) -> ClarifyResponse:
        """Apply business rules on top of the raw LLM structured output."""
        if is_first_turn or (
            llm_output.needs_more_info and self._questions_asked < MAX_QUESTIONS
        ):
            if is_first_turn and not llm_output.needs_more_info:
                llm_output.needs_more_info = True

            question = llm_output.questions[0] if llm_output.questions else ""
            if not question.strip():
                question = _FIRST_TURN_FALLBACK

            self._questions_asked += 1
            return ClarifyResponse(needs_more_info=True, questions=[question])

        if llm_output.context is not None:
            return ClarifyResponse(
                needs_more_info=False,
                context=llm_output.context,
            )

        return self._force_complete_context()

    def _force_complete_context(self) -> ClarifyResponse:
        """Emit best-effort context when the question budget is exhausted."""
        logger.info("[%s] Forcing context completion", self.session_id)
        system = SystemMessage(
            content=(
                "Based on the conversation, produce the best possible structured "
                "context for PRD generation. Use reasonable inferences from what "
                "was discussed; leave tech_preferences null if unknown."
            )
        )
        context: ClarifyContext = self._fallback_llm.invoke([system, *self._history])
        return ClarifyResponse(needs_more_info=False, context=context)

    @staticmethod
    def _serialize_assistant_turn(response: ClarifyResponse) -> str:
        if response.needs_more_info:
            return response.questions[0] if response.questions else "Clarifying..."
        if response.context:
            return (
                "¡Perfecto, creo que tengo todo lo que necesito para armar "
                f"el documento! {response.context.description[:80]}"
            )
        return "Clarification complete."

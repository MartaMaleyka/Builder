"""Frontend QA Agent: evaluates and rewrites JSX components against UI/UX criteria."""

from __future__ import annotations

import json

from langchain_ollama import ChatOllama

from agents.code_llm import OLLAMA_BASE_URL, FRONTEND_MODEL
from models.schemas import GeneratedFile, PRDDocument

EVALUATION_PROMPT = """You are a senior UI/UX code reviewer.
Evaluate this React component and return ONLY a JSON object.

Component path: {file_path}
Component code:
{code}

Score each criterion from 0 to 10:
- layout_score: has sidebar/navbar/proper page structure
- states_score: handles loading skeleton, error state, empty state
- interactivity: has action buttons, modals, or forms
- visual_richness: uses cards, badges, grids, shadows, hover effects
- tailwind_usage: uses varied and meaningful Tailwind classes

Also set:
- needs_rewrite: true if average score < 7
- issues: list of specific problems found (max 5)

Return ONLY this JSON, nothing else:
{{
  "layout_score": 0,
  "states_score": 0,
  "interactivity": 0,
  "visual_richness": 0,
  "tailwind_usage": 0,
  "average": 0,
  "needs_rewrite": true,
  "issues": []
}}"""

REWRITE_PROMPT = """You are a senior UI/UX frontend engineer.
Rewrite this React component to fix these specific issues:

File: {file_path}
Project: {project_title}
Entities: {entities}

Issues found in previous version:
{issues}

Original code (improve this, don't start from scratch):
{original_code}

MANDATORY fixes based on issues:
{mandatory_fixes}

ALWAYS include in the rewrite:
1. If App.jsx: sidebar with nav links (one per entity), emoji icons,
   active state indicator, app title at top
2. If Page component: page header + stats row + card grid OR table
   + loading skeleton (animate-pulse) + empty state with icon + CTA
3. If Card component: status badge + hover effects + action buttons
   (group hover pattern: opacity-0 group-hover:opacity-100)
4. Fetch with loading/error/empty handling
5. At least one modal for create/edit with form fields
6. Transitions: transition-all duration-200 on interactive elements

Write ONLY the complete JSX code, no explanations, no markdown fences:"""


class FrontendQAAgent:
    """Evaluates JSX files against UI/UX criteria and rewrites failing ones."""

    def __init__(self) -> None:
        self.eval_llm = ChatOllama(
            model=FRONTEND_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0.0,
            num_predict=512,
        )
        self.rewrite_llm = ChatOllama(
            model=FRONTEND_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0.2,
            num_predict=4096,
        )

    def _clean_markdown(self, text: str) -> str:
        """Remove markdown code fences safely."""
        text = text.strip()
        if not text:
            return text
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()

    async def evaluate(self, file_path: str, code: str) -> dict:
        prompt = EVALUATION_PROMPT.format(file_path=file_path, code=code[:3000])
        response = await self.eval_llm.ainvoke(prompt)
        raw = response.content if isinstance(response.content, str) else str(response.content)
        raw = self._clean_markdown(raw)

        try:
            result = json.loads(raw)
            scores = [
                result.get("layout_score", 0),
                result.get("states_score", 0),
                result.get("interactivity", 0),
                result.get("visual_richness", 0),
                result.get("tailwind_usage", 0),
            ]
            result["average"] = sum(scores) / len(scores)
            result["needs_rewrite"] = result["average"] < 7
            print(
                f"[QAAgent] {file_path}: avg={result['average']:.1f} "
                f"rewrite={result['needs_rewrite']}"
            )
            print(f"[QAAgent] Issues: {result.get('issues', [])}")
            return result
        except json.JSONDecodeError:
            print(f"[QAAgent] JSON parse failed for {file_path}, forcing rewrite")
            return {"needs_rewrite": True, "average": 0, "issues": ["Could not evaluate"]}

    def _build_mandatory_fixes(self, issues: list[str], file_path: str) -> str:
        fixes: list[str] = []
        for issue in issues:
            issue_lower = issue.lower()
            if "sidebar" in issue_lower or "nav" in issue_lower or "layout" in issue_lower:
                fixes.append(
                    "- ADD: full sidebar with w-64, nav links per entity, active state"
                )
            if "loading" in issue_lower or "skeleton" in issue_lower:
                fixes.append("- ADD: animate-pulse skeleton loader while fetching")
            if "empty" in issue_lower:
                fixes.append("- ADD: empty state with SVG icon + message + CTA button")
            if "error" in issue_lower:
                fixes.append("- ADD: error state with message + retry button")
            if "modal" in issue_lower or "form" in issue_lower:
                fixes.append(
                    "- ADD: modal with form for create/edit, overlay + close on ESC"
                )
            if "card" in issue_lower or "grid" in issue_lower:
                fixes.append("- ADD: card grid with shadow, hover effects, status badges")
            if "badge" in issue_lower or "status" in issue_lower:
                fixes.append("- ADD: pill badges with semantic colors per status value")
            if "transition" in issue_lower or "hover" in issue_lower:
                fixes.append(
                    "- ADD: hover:shadow-lg hover:-translate-y-1 transition-all duration-200"
                )
        if fixes:
            return "\n".join(fixes)
        return "- Improve overall visual quality and add missing UI patterns"

    async def rewrite(
        self,
        file_path: str,
        original_code: str,
        issues: list[str],
        prd: PRDDocument,
    ) -> str:
        entities = [e.name for e in prd.data_model]
        mandatory_fixes = self._build_mandatory_fixes(issues, file_path)

        prompt = REWRITE_PROMPT.format(
            file_path=file_path,
            project_title=prd.title,
            entities=entities,
            issues="\n".join(f"- {i}" for i in issues),
            original_code=original_code,
            mandatory_fixes=mandatory_fixes,
        )
        response = await self.rewrite_llm.ainvoke(prompt)
        content = response.content if isinstance(response.content, str) else str(response.content)
        content = self._clean_markdown(content)

        print(f"[QAAgent] Rewrite complete: {file_path} ({len(content)} chars)")
        return content

    async def process(
        self,
        file: GeneratedFile,
        prd: PRDDocument,
        max_iterations: int = 2,
    ) -> GeneratedFile:
        if not file.path.endswith((".jsx", ".tsx")):
            return file
        if len(file.content.strip()) < 100:
            print(f"[QAAgent] Skipping {file.path}: too short")
            return file

        current_code = file.content
        for iteration in range(max_iterations):
            print(f"[QAAgent] Evaluating {file.path} (iteration {iteration + 1})")
            evaluation = await self.evaluate(file.path, current_code)

            if not evaluation.get("needs_rewrite"):
                avg = evaluation.get("average", 0)
                print(f"[QAAgent] ✓ {file.path} passed (avg={avg:.1f})")
                break

            print(f"[QAAgent] ✗ Rewriting {file.path}...")
            current_code = await self.rewrite(
                file_path=file.path,
                original_code=current_code,
                issues=evaluation.get("issues", []),
                prd=prd,
            )

        file.content = current_code
        return file

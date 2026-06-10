"""Helper utilities for the code generation pipeline."""

from __future__ import annotations

from typing import Optional

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from models.schemas import (
    GeneratedFile,
    GenerationResult,
    GenerationStatus,
    ModuleFileOutput,
    ModuleState,
    ModuleStatus,
)


def init_generation_result(session_id: str, module_names: list[str]) -> GenerationResult:
    return GenerationResult(
        session_id=session_id,
        modules=[
            ModuleStatus(module_name=name, status=ModuleState.PENDING)
            for name in module_names
        ],
        total_files=0,
        status=GenerationStatus.IN_PROGRESS,
    )


def set_module_state(
    result: GenerationResult, module_name: str, status: ModuleState, error: Optional[str] = None
) -> None:
    for mod in result.modules:
        if mod.module_name == module_name:
            mod.status = status
            mod.error = error
            return


def save_module_files(
    result: GenerationResult,
    module_name: str,
    raw_files: list[ModuleFileOutput],
) -> list[GeneratedFile]:
    files = [
        GeneratedFile(path=f.path, content=f.content, module=module_name)
        for f in raw_files
    ]
    for mod in result.modules:
        if mod.module_name == module_name:
            mod.files = files
            mod.status = ModuleState.DONE
            mod.error = None
            break
    result.total_files = sum(len(m.files) for m in result.modules)
    return files


def mark_module_failed(result: GenerationResult, module_name: str, error: str) -> None:
    for mod in result.modules:
        if mod.module_name == module_name:
            mod.status = ModuleState.FAILED
            mod.error = error
            mod.files = []
            break
    result.total_files = sum(len(m.files) for m in result.modules)


def finalize_result(result: GenerationResult) -> None:
    failed = sum(1 for m in result.modules if m.status == ModuleState.FAILED)
    done = sum(1 for m in result.modules if m.status == ModuleState.DONE)
    if done == 0 and failed > 0:
        result.status = GenerationStatus.FAILED
    else:
        result.status = GenerationStatus.COMPLETE
    result.total_files = sum(len(m.files) for m in result.modules)


def build_context_messages(prior_modules: list[ModuleStatus]) -> list[BaseMessage]:
    """Convert completed modules into LLM context messages."""
    messages: list[BaseMessage] = []
    for mod in prior_modules:
        if mod.status != ModuleState.DONE or not mod.files:
            continue
        summary = "\n".join(
            f"--- {f.path} ---\n{f.content[:2000]}" for f in mod.files[:8]
        )
        messages.append(
            HumanMessage(content=f"Previously generated module '{mod.module_name}':")
        )
        messages.append(AIMessage(content=summary))
    return messages


def all_generated_files(result: GenerationResult) -> list[GeneratedFile]:
    files: list[GeneratedFile] = []
    for mod in result.modules:
        if mod.status == ModuleState.DONE:
            files.extend(mod.files)
    return files

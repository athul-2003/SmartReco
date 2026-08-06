"""
Phase 6 (FR-7, bonus): LangSmith tracing for the LangGraph pipeline
(agent/graph.py). LangSmith's own SDK auto-instruments every LangGraph run
purely by reading env vars at call time - no code-path branching or
explicit tracer wiring needed in agent/graph.py itself. The catch:
pydantic-settings parses those into our own Settings object, it doesn't set
os.environ - so this propagates them across, once, at startup.

Sets both the current SDK's preferred `LANGSMITH_*` names and the legacy
`LANGCHAIN_*` names (still the SRS's own wording for this bonus, and still
checked as a fallback by the installed langsmith SDK - confirmed by reading
its source, langsmith/utils.py's get_env_var(namespaces=("LANGSMITH",
"LANGCHAIN"))) - LANGSMITH_* takes precedence when both are set, so this is
correct either way, robust to which SDK version ends up installed.

Also sets the bare `*_TRACING` name (no `_V2`) alongside `*_TRACING_V2` -
LangSmith's current dashboard quickstart snippet shows `LANGSMITH_TRACING`
now, dropping the `_V2` suffix as the SDK's newer convention. Reading
tracing_is_enabled()'s actual precedence chain confirms `*_TRACING_V2` is
still checked first when both are present, so this was never a behavior
bug - but setting both keeps this file's env vars matching the official
docs a developer would actually see, not just "technically equivalent."
"""

import os

from app.config import Settings


def configure_langsmith(settings: Settings) -> None:
    if not (settings.langchain_tracing_v2 and settings.langchain_api_key):
        return
    for prefix in ("LANGSMITH", "LANGCHAIN"):
        os.environ[f"{prefix}_TRACING_V2"] = "true"
        os.environ[f"{prefix}_TRACING"] = "true"
        os.environ[f"{prefix}_API_KEY"] = settings.langchain_api_key
        os.environ[f"{prefix}_PROJECT"] = settings.langchain_project

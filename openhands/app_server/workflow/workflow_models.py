from enum import Enum

from pydantic import BaseModel, Field

DEFAULT_REVIEW_PROMPT = """Review the current implementation and produce or update REVIEW.md.

Required output contract:
1. Start with exactly one verdict token:
   - REVIEW_VERDICT:PASS
   - REVIEW_VERDICT:FAIL
2. If FAIL, include a flat findings list with concrete file paths and fix guidance.
3. End with a short "Next action" section for the implementation agent.

Review focus:
- Correctness and regressions
- Missing tests or weak coverage
- Safety and reliability risks
- Scope drift from PLAN.md
"""

DEFAULT_CONTEXTKING_PROTOCOL_FILE = '/opt/contextking/rules/ck-code-search-protocol.md'


def load_contextking_protocol_file(protocol_file: str) -> str | None:
    """Load the full ContextKing protocol markdown from disk.

    Returns None when the file is missing, unreadable, or empty after trimming.
    """
    try:
        with open(protocol_file, encoding='utf-8') as f:
            content = f.read().strip()
            return content if content else None
    except OSError:
        return None


class WorkflowPhase(str, Enum):
    PLAN = 'plan'
    IMPLEMENT = 'implement'
    REVIEW = 'review'


class WorkflowSettings(BaseModel):
    enabled: bool = True
    plan_model: str | None = 'google/gemini-3.1-flash-lite-preview'
    implement_model: str | None = 'deepseek/deepseek-v4-flash'
    review_model: str | None = 'z-ai/glm-5.1'
    review_prompt: str | None = Field(default=DEFAULT_REVIEW_PROMPT)
    strict_enforcement: bool = True
    require_context_king: bool = True
    max_review_iterations: int = Field(default=3, ge=1, le=10)

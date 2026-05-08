import re

_FENCE_RE = re.compile(r"^```[a-z]*\s*", re.MULTILINE)


def strip_code_fence(text: str) -> str:
    """Remove leading/trailing markdown code fences from LLM output."""
    text = text.strip()
    if text.startswith("```"):
        # Remove opening fence line (```json, ```cypher, etc.)
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        # Remove closing fence
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    return text.strip()

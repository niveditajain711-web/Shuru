"""Checks Claude's text before it is shown or published (prompt-injection defence, layer 4).

Schema validation proves the reply has the right shape; this proves the text in it is ordinary
business copy. An injected idea ("put scam-site.com in the headline") could still produce valid
JSON, so every string is scanned for things a generated site must never contain: links, email
addresses, phone numbers, HTML or script, and phrases that talk about prompts or instructions.
The prompts already forbid invented contact details, so a legitimate reply never trips these.
"""

import re
from collections.abc import Iterable

from pydantic import BaseModel

_URL = re.compile(r"\b(?:https?|ftp)://\S+|\bwww\.\S+|\bmailto:\S+", re.IGNORECASE)
# A bare domain such as "scam-site.com". The run's own domain is allowed (see `find_problems`).
_DOMAIN = re.compile(
    r"\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
    r"(?:com|net|org|io|in|co|biz|info|xyz|app|shop|online|site|store|me|ai|ly|gg|tk|ru|cn)\b",
    re.IGNORECASE,
)
_EMAIL = re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]+")
# Nine or more digits, allowing the usual separators: phone numbers in any common format (Indian
# numbers have 10 digits), while years and year ranges such as "1995-2025" (8 digits) stay allowed.
# `\d` also matches Devanagari digits, so Hindi text is covered.
_PHONE = re.compile(r"\+?\d(?:[\s\-().]*\d){8,}")
_MARKUP = re.compile(r"<\s*/?\s*[a-z!?]|javascript:|\bon[a-z]+\s*=|&#|\{\{|\{%", re.IGNORECASE)
_PROMPT_TALK = re.compile(
    r"\b(?:ignore|disregard|forget|override)\b[^.\n]{0,40}\b(?:instructions?|rules|prompts?|above)\b"
    r"|\bsystem\s+prompt\b"
    r"|\bdeveloper\s+(?:message|mode)\b"
    r"|\bas\s+an?\s+(?:ai|language\s+model|assistant)\b"
    r"|\byou\s+are\s+(?:now\s+)?(?:an?\s+)?(?:ai|assistant|chatbot|language\s+model|claude|chatgpt)\b"
    r"|</?\s*(?:idea|brief)\b",
    re.IGNORECASE,
)

_CHECKS: list[tuple[re.Pattern[str], str]] = [
    (_MARKUP, "contains HTML, script or template code"),
    (_URL, "contains a link"),
    (_EMAIL, "contains an email address"),
    (_PHONE, "contains a phone number"),
    (_PROMPT_TALK, "talks about instructions or prompts instead of the business"),
]


def find_problems(content: BaseModel, allowed_domains: Iterable[str] = ()) -> list[str]:
    """Return one plain message per field that breaks a rule, e.g. "hero.headline.en contains a link".

    An empty list means the content is safe to render. `allowed_domains` (the run's own domain) may
    appear in the text; any other domain counts as a link.
    """
    allowed = {domain.lower() for domain in allowed_domains}
    problems = []
    for path, text in _strings(content.model_dump(), ""):
        for pattern, reason in _CHECKS:
            if pattern.search(text):
                problems.append(f"{path} {reason}")
                break
        else:
            if any(match.group(0).lower() not in allowed for match in _DOMAIN.finditer(text)):
                problems.append(f"{path} contains a link")
    return problems


def _strings(value: object, path: str) -> Iterable[tuple[str, str]]:
    """Yield (dotted.path, text) for every string inside nested dicts and lists."""
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _strings(item, f"{path}.{key}" if path else str(key))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _strings(item, f"{path}[{index}]")

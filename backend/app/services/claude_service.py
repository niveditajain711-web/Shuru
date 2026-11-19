import json
import logging
import time
from collections.abc import Callable

import anthropic
from pydantic import BaseModel, ValidationError

from app.core.config import Settings
from app.core.errors import ClaudeError
from app.models import Brief, Lang, SiteContent
from app.services import prompts
from app.services.content_check import find_problems

logger = logging.getLogger(__name__)

# One retry after an invalid answer, as the PRD requires (two attempts in total).
_MAX_ATTEMPTS = 2


class ClaudeService:
    """Claude generates structured JSON at fixed points. It has no tools and decides nothing.

    Every reply must match its schema and pass the content check (`content_check.find_problems`):
    no links, contact details, markup or prompt talk. Either failure gets one retry, then an error.
    """

    def __init__(self, client: anthropic.Anthropic, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    def generate_brief(self, idea: str, lang: Lang) -> Brief:
        return self._generate(
            call="brief",
            model=self._settings.brief_model,
            max_tokens=self._settings.brief_max_tokens,
            effort="low",
            system=prompts.BRIEF_SYSTEM,
            user=prompts.brief_user_message(idea, lang),
            schema=Brief,
            check=find_problems,
        )

    def generate_site(self, brief: Brief, domain: str) -> SiteContent:
        return self._generate(
            call="site",
            model=self._settings.site_model,
            max_tokens=self._settings.site_max_tokens,
            effort="medium",
            system=prompts.SITE_SYSTEM,
            user=prompts.site_user_message(brief.model_dump_json(), domain),
            schema=SiteContent,
            # The site may mention its own domain; any other domain counts as a link.
            check=lambda site: find_problems(site, allowed_domains=[domain]),
        )

    def _generate[T: BaseModel](
        self,
        *,
        call: str,
        model: str,
        max_tokens: int,
        effort: str,
        system: str,
        user: str,
        schema: type[T],
        check: Callable[[T], list[str]],
    ) -> T:
        # The schema is serialised with sorted keys so the cached system prompt is byte-stable.
        schema_json = json.dumps(schema.model_json_schema(), sort_keys=True)
        system_blocks = [
            {"type": "text", "text": system + schema_json, "cache_control": {"type": "ephemeral"}}
        ]
        messages: list[dict] = [{"role": "user", "content": user}]

        for attempt in range(1, _MAX_ATTEMPTS + 1):
            text = self._request(call, model, max_tokens, effort, system_blocks, messages, attempt)
            try:
                result = schema.model_validate_json(_extract_json(text))
            except ValidationError as exc:
                logger.warning("claude invalid output call=%s attempt=%d error=%s", call, attempt, exc)
                feedback = f"That JSON was invalid: {exc}\nReply again with corrected JSON only."
            else:
                problems = check(result)
                if not problems:
                    return result
                # Logged as field paths and reasons only, so visitor text never reaches the logs.
                logger.warning("claude unsafe output call=%s attempt=%d problems=%s", call, attempt, problems)
                feedback = (
                    "That JSON broke the content rules: "
                    + "; ".join(problems)
                    + ". Website text must not contain links, domains, email addresses, phone numbers, "
                    "HTML or code, or talk about instructions. Reply again with corrected JSON only."
                )
            messages += [
                {"role": "assistant", "content": text},
                {"role": "user", "content": feedback},
            ]

        logger.error("claude gave up call=%s attempts=%d", call, _MAX_ATTEMPTS)
        raise ClaudeError()

    def _request(
        self,
        call: str,
        model: str,
        max_tokens: int,
        effort: str,
        system_blocks: list[dict],
        messages: list[dict],
        attempt: int,
    ) -> str:
        """Make one API call and return its text, or raise ClaudeError."""
        started = time.monotonic()
        try:
            response = self._client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system_blocks,
                messages=messages,
                output_config={"effort": effort},
                timeout=self._settings.claude_timeout_seconds,
            )
        except anthropic.APIError as exc:
            logger.error("claude api error call=%s attempt=%d error=%r", call, attempt, exc)
            raise ClaudeError() from exc

        usage = response.usage
        logger.info(
            "claude call=%s model=%s attempt=%d stop_reason=%s input_tokens=%d output_tokens=%d "
            "cache_read_tokens=%s cache_write_tokens=%s duration=%.2fs",
            call,
            model,
            attempt,
            response.stop_reason,
            usage.input_tokens,
            usage.output_tokens,
            usage.cache_read_input_tokens,
            usage.cache_creation_input_tokens,
            time.monotonic() - started,
        )
        if response.stop_reason in ("refusal", "max_tokens"):
            logger.error("claude unusable response call=%s stop_reason=%s", call, response.stop_reason)
            raise ClaudeError()
        return "".join(block.text for block in response.content if block.type == "text")


def _extract_json(text: str) -> str:
    """Return the outermost JSON object in `text`, tolerating stray prose or code fences."""
    start, end = text.find("{"), text.rfind("}")
    return text[start : end + 1] if start != -1 and end > start else text

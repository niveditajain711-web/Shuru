import json
from types import SimpleNamespace

import anthropic
import httpx
import pytest

from app.core.config import Settings
from app.core.errors import ClaudeError
from app.models import Lang
from app.services.claude_service import ClaudeService
from tests.conftest import NAME_IDEAS, make_brief

VALID_BRIEF = {
    "audience": "Home cooks",
    "tone": "Warm",
    "tagline": "Pickles like home",
    "name_ideas": NAME_IDEAS,
}


def reply(text: str, stop_reason: str = "end_turn"):
    usage = SimpleNamespace(
        input_tokens=10, output_tokens=20, cache_read_input_tokens=0, cache_creation_input_tokens=0
    )
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)], stop_reason=stop_reason, usage=usage
    )


class FakeAnthropic:
    """Returns queued replies (or raises queued exceptions) and records each request."""

    def __init__(self, *outcomes) -> None:
        self.outcomes = list(outcomes)
        self.requests: list[dict] = []
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.requests.append(kwargs)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def service(*outcomes) -> tuple[ClaudeService, FakeAnthropic]:
    client = FakeAnthropic(*outcomes)
    return ClaudeService(client, Settings()), client


def test_valid_brief_is_returned():
    claude, client = service(reply(json.dumps(VALID_BRIEF)))

    assert claude.generate_brief("pickles", Lang.EN) == make_brief()
    request = client.requests[0]
    assert request["model"] == "claude-haiku-5-5"
    assert request["system"][0]["cache_control"] == {"type": "ephemeral"}


def test_json_inside_code_fence_is_accepted():
    claude, _ = service(reply("```json\n" + json.dumps(VALID_BRIEF) + "\n```"))

    assert claude.generate_brief("pickles", Lang.EN) == make_brief()


def test_invalid_output_is_retried_once_with_the_error():
    claude, client = service(reply('{"audience": "x"}'), reply(json.dumps(VALID_BRIEF)))

    assert claude.generate_brief("pickles", Lang.EN) == make_brief()
    retry_messages = client.requests[1]["messages"]
    assert retry_messages[1]["role"] == "assistant"
    assert "invalid" in retry_messages[2]["content"]


def test_gives_up_after_one_retry():
    claude, client = service(reply("not json"), reply("still not json"))

    with pytest.raises(ClaudeError):
        claude.generate_brief("pickles", Lang.EN)
    assert len(client.requests) == 2


def test_name_ideas_must_be_valid_domain_labels():
    bad = {**VALID_BRIEF, "name_ideas": ["has space"] * 8}
    claude, _ = service(reply(json.dumps(bad)), reply(json.dumps(bad)))

    with pytest.raises(ClaudeError):
        claude.generate_brief("pickles", Lang.EN)


@pytest.mark.parametrize("stop_reason", ["refusal", "max_tokens"])
def test_unusable_stop_reason_fails_without_retry(stop_reason):
    claude, client = service(reply(json.dumps(VALID_BRIEF), stop_reason))

    with pytest.raises(ClaudeError):
        claude.generate_brief("pickles", Lang.EN)
    assert len(client.requests) == 1


def test_api_error_becomes_claude_error():
    error = anthropic.APIConnectionError(request=httpx.Request("POST", "https://api.anthropic.com"))
    claude, _ = service(error)

    with pytest.raises(ClaudeError):
        claude.generate_brief("pickles", Lang.EN)

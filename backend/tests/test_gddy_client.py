import subprocess

import pytest

from app.errors import GddyError
from app.models import DomainOffer
from app.services.gddy_client import GddyClient


def completed(stdout: str = "", returncode: int = 0, stderr: str = ""):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


@pytest.fixture
def gddy() -> GddyClient:
    return GddyClient("gddy", "ote", 5)


def patch_run(monkeypatch, result):
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(subprocess, "run", fake_run)
    return calls


def test_suggest_builds_an_argument_list_without_a_shell(gddy, monkeypatch):
    calls = patch_run(monkeypatch, completed('[{"domain": "achaar.com"}, {"domain": "achaar.io"}]'))

    assert gddy.suggest("achaar", ["com", "io"], 5) == ["achaar.com", "achaar.io"]
    command, kwargs = calls[0]
    assert command == [
        "gddy", "domain", "suggest", "achaar", "--tlds", "com,io", "--limit", "5", "--json", "--env", "ote",
    ]
    assert kwargs["timeout"] == 5
    assert "shell" not in kwargs


def test_available_domain_returns_offer(gddy, monkeypatch):
    patch_run(monkeypatch, completed('{"domain": "achaar.com", "available": true, "price": 12.5, "currency": "USD"}'))

    assert gddy.check_availability("achaar.com") == DomainOffer(name="achaar.com", price=12.5, currency="USD")


def test_taken_domain_returns_none(gddy, monkeypatch):
    patch_run(monkeypatch, completed('{"domain": "achaar.com", "available": false}'))

    assert gddy.check_availability("achaar.com") is None


def test_available_domain_without_price_is_an_error(gddy, monkeypatch):
    patch_run(monkeypatch, completed('{"domain": "achaar.com", "available": true}'))

    with pytest.raises(GddyError):
        gddy.check_availability("achaar.com")


@pytest.mark.parametrize("query", ["a b", "a;b", "$(x)", "UPPER", "", "-x-"])
def test_unsafe_query_is_rejected_before_running(gddy, monkeypatch, query):
    calls = patch_run(monkeypatch, completed("[]"))

    with pytest.raises(GddyError):
        gddy.suggest(query, ["com"], 5)
    assert calls == []


@pytest.mark.parametrize("domain", ["nodot", "a.com; ls", "a b.com", "../x.com"])
def test_unsafe_domain_is_rejected_before_running(gddy, monkeypatch, domain):
    calls = patch_run(monkeypatch, completed("{}"))

    with pytest.raises(GddyError):
        gddy.check_availability(domain)
    assert calls == []


@pytest.mark.parametrize(
    "result",
    [
        completed(returncode=1, stderr="boom"),
        completed(stdout="not json"),
        completed(stdout='{"unexpected": true}'),
        subprocess.TimeoutExpired(cmd="gddy", timeout=5),
        FileNotFoundError("gddy"),
    ],
)
def test_failures_become_gddy_error(gddy, monkeypatch, result):
    patch_run(monkeypatch, result)

    with pytest.raises(GddyError):
        gddy.check_availability("achaar.com")

import pytest

from app.errors import GddyError
from app.models import DomainOffer
from app.services.domain_service import DomainService


class FakeGddy:
    def __init__(self, suggestions, availability) -> None:
        self.suggestions = suggestions
        self.availability = availability
        self.suggest_queries: list[str] = []

    def suggest(self, query, tlds, limit):
        self.suggest_queries.append(query)
        result = self.suggestions[query]
        if isinstance(result, Exception):
            raise result
        return result

    def check_availability(self, domain):
        result = self.availability[domain]
        if isinstance(result, Exception):
            raise result
        return result


def offer(name: str) -> DomainOffer:
    return DomainOffer(name=name, price=10.0, currency="USD")


def test_merges_dedupes_and_keeps_only_available():
    gddy = FakeGddy(
        suggestions={"a": ["a.com", "shared.com"], "b": ["shared.com", "b.com"]},
        availability={"a.com": offer("a.com"), "shared.com": None, "b.com": offer("b.com")},
    )

    assert DomainService(gddy).find_available(["a", "b"]) == [offer("a.com"), offer("b.com")]


def test_only_the_first_names_are_searched():
    gddy = FakeGddy({n: [] for n in "abcde"}, {})

    DomainService(gddy).find_available(list("abcde"))

    assert sorted(gddy.suggest_queries) == ["a", "b", "c"]


def test_no_suggestions_returns_empty_list():
    assert DomainService(FakeGddy({"a": []}, {})).find_available(["a"]) == []


def test_a_failed_check_is_skipped():
    gddy = FakeGddy(
        suggestions={"a": ["a.com", "b.com"]},
        availability={"a.com": GddyError(), "b.com": offer("b.com")},
    )

    assert DomainService(gddy).find_available(["a"]) == [offer("b.com")]


def test_a_failed_suggestion_is_skipped():
    gddy = FakeGddy(
        suggestions={"a": GddyError(), "b": ["b.com"]},
        availability={"b.com": offer("b.com")},
    )

    assert DomainService(gddy).find_available(["a", "b"]) == [offer("b.com")]


def test_error_when_every_suggestion_fails():
    gddy = FakeGddy({"a": GddyError(), "b": GddyError()}, {})

    with pytest.raises(GddyError):
        DomainService(gddy).find_available(["a", "b"])


def test_error_when_every_check_fails():
    gddy = FakeGddy({"a": ["a.com", "b.com"]}, {"a.com": GddyError(), "b.com": GddyError()})

    with pytest.raises(GddyError):
        DomainService(gddy).find_available(["a"])

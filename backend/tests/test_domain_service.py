import pytest

from app.core.errors import DomainTakenError, GddyError
from app.models import DomainOffer
from app.services.domain_service import DomainService


class FakeGddy:
    def __init__(self, suggestions=None, availability=None) -> None:
        self.suggestions = suggestions or {}
        self.availability = availability or {}
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


def offer(name: str, price: float = 10.0) -> DomainOffer:
    return DomainOffer(name=name, price=price, currency="USD")


def test_merges_and_dedupes_suggestions_keeping_the_first():
    gddy = FakeGddy({"a": [offer("a.com"), offer("shared.com", 1)], "b": [offer("shared.com", 2), offer("b.com")]})

    result = DomainService(gddy).find_available(["a", "b"])

    assert result == [offer("a.com"), offer("shared.com", 1), offer("b.com")]


def test_suggestions_are_not_rechecked_for_availability():
    gddy = FakeGddy({"a": [offer("a.com")]})  # check_availability would raise KeyError

    assert DomainService(gddy).find_available(["a"]) == [offer("a.com")]


def test_only_the_first_names_are_searched():
    gddy = FakeGddy({n: [] for n in "abcde"})

    DomainService(gddy).find_available(list("abcde"))

    assert sorted(gddy.suggest_queries) == ["a", "b", "c"]


def test_results_are_capped():
    gddy = FakeGddy({"a": [offer(f"a{i}.com") for i in range(15)]})

    assert len(DomainService(gddy).find_available(["a"])) == 10


def test_no_suggestions_returns_empty_list():
    assert DomainService(FakeGddy({"a": []})).find_available(["a"]) == []


def test_a_failed_suggestion_is_skipped():
    gddy = FakeGddy({"a": GddyError(), "b": [offer("b.com")]})

    assert DomainService(gddy).find_available(["a", "b"]) == [offer("b.com")]


def test_error_when_every_suggestion_fails():
    gddy = FakeGddy({"a": GddyError(), "b": GddyError()})

    with pytest.raises(GddyError):
        DomainService(gddy).find_available(["a", "b"])


def test_confirm_available_returns_the_fresh_offer():
    gddy = FakeGddy(availability={"a.com": offer("a.com", 11.0)})

    assert DomainService(gddy).confirm_available("a.com") == offer("a.com", 11.0)


def test_confirm_available_rejects_a_taken_domain():
    gddy = FakeGddy(availability={"a.com": None})

    with pytest.raises(DomainTakenError):
        DomainService(gddy).confirm_available("a.com")

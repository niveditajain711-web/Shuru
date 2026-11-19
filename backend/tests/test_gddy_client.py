import json

import httpx
import pytest

from app.core.errors import GddyError
from app.models import DomainOffer
from app.clients.gddy_client import GddyClient

BASE = "https://api.example.test/v3/domains"

# Shape taken from a real response of GET /v3/domains/suggestions.
SUGGESTIONS = {
    "items": [
        {
            "domain": "sunrisebakeryco.com",
            "inventory": "REGISTRY",
            "prices": [
                {
                    "period": 1,
                    "price": {"currencyCode": "USD", "value": 919},
                    "recommended": True,
                    "renewalPrice": {"currencyCode": "USD", "value": 1159},
                    "term": "YEAR",
                },
                {
                    "period": 2,
                    "price": {"currencyCode": "USD", "value": 2078},
                    "renewalPrice": {"currencyCode": "USD", "value": 2318},
                    "term": "YEAR",
                },
            ],
        },
        {"domain": "noprice.com", "inventory": "REGISTRY", "prices": []},
    ]
}


def availability(**item):
    return {"items": [{"domain": "achaar.com", **item}]}


def one_year(value=919, currency="USD", renewal=1159):
    return {"period": 1, "term": "YEAR", "price": {"currencyCode": currency, "value": value},
            "renewalPrice": {"currencyCode": currency, "value": renewal}}


def make_client(handler) -> tuple[GddyClient, list[httpx.Request]]:
    requests: list[httpx.Request] = []

    def record(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return handler(request)

    http = httpx.Client(transport=httpx.MockTransport(record))
    return GddyClient(BASE + "/", "secret-pat", 5, http=http), requests


def respond(body=None, status=200, headers=None):
    return lambda request: httpx.Response(status, json=body, headers=headers)


def test_suggest_sends_a_bearer_request_and_converts_prices():
    client, requests = make_client(respond(SUGGESTIONS))

    offers = client.suggest("sunrisebakery", ["com", "net"], 5)

    assert offers == [DomainOffer(name="sunrisebakeryco.com", price=9.19, renewal_price=11.59, currency="USD")]
    request = requests[0]
    assert request.method == "GET"
    assert request.url.path == "/v3/domains/suggestions"
    assert request.url.params["query"] == "sunrisebakery"
    assert request.url.params["tlds"] == "com,net"
    assert request.url.params["pageSize"] == "5"
    assert request.headers["Authorization"] == "Bearer secret-pat"


def test_check_availability_sends_one_accurate_check():
    client, requests = make_client(respond(availability(available=True, prices=[one_year()])))

    offer = client.check_availability("achaar.com")

    assert offer == DomainOffer(name="achaar.com", price=9.19, renewal_price=11.59, currency="USD")
    assert requests[0].method == "POST"
    assert requests[0].url.path == "/v3/domains/check-availability"
    assert json.loads(requests[0].content) == {"domains": ["achaar.com"], "optimizeFor": "ACCURACY"}


def test_taken_domain_returns_none():
    client, _ = make_client(respond(availability(available=False)))

    assert client.check_availability("achaar.com") is None


def test_domain_that_cannot_be_checked_returns_none():
    error = {"name": "UNSUPPORTED_TLD", "correlationId": "abc", "message": "no"}
    client, _ = make_client(respond(availability(error=error)))

    assert client.check_availability("achaar.com") is None


def test_available_domain_without_a_one_year_price_is_an_error():
    client, _ = make_client(respond(availability(available=True, prices=[])))

    with pytest.raises(GddyError):
        client.check_availability("achaar.com")


@pytest.mark.parametrize(
    "value, currency, expected",
    [(919, "USD", 9.19), (1500, "JPY", 1500.0), (12345, "KWD", 12.345), (5, "USD", 0.05)],
)
def test_prices_use_the_currency_decimals(value, currency, expected):
    client, _ = make_client(respond(availability(available=True, prices=[one_year(value, currency, value)])))

    assert client.check_availability("achaar.com").price == expected


def test_renewal_in_another_currency_is_dropped():
    price = one_year()
    price["renewalPrice"]["currencyCode"] = "EUR"
    client, _ = make_client(respond(availability(available=True, prices=[price])))

    assert client.check_availability("achaar.com").renewal_price is None


def test_rate_limit_is_retried_once(monkeypatch):
    monkeypatch.setattr("app.clients.gddy_client.time.sleep", lambda seconds: None)
    responses = iter([httpx.Response(429, headers={"Retry-After": "1"}), httpx.Response(200, json=SUGGESTIONS)])
    client, requests = make_client(lambda request: next(responses))

    assert len(client.suggest("sunrisebakery", ["com"], 5)) == 1
    assert len(requests) == 2


def test_persistent_rate_limit_is_an_error(monkeypatch):
    monkeypatch.setattr("app.clients.gddy_client.time.sleep", lambda seconds: None)
    client, requests = make_client(respond({"name": "TOO_MANY_REQUESTS"}, status=429))

    with pytest.raises(GddyError):
        client.suggest("sunrisebakery", ["com"], 5)
    assert len(requests) == 2


@pytest.mark.parametrize("status", [400, 401, 403, 422, 500, 503])
def test_error_statuses_become_gddy_error(status):
    client, _ = make_client(respond({"name": "X", "correlationId": "c", "message": "m"}, status=status))

    with pytest.raises(GddyError):
        client.suggest("sunrisebakery", ["com"], 5)


def test_empty_body_becomes_gddy_error():
    client, _ = make_client(lambda request: httpx.Response(200, content=b""))

    with pytest.raises(GddyError):
        client.suggest("sunrisebakery", ["com"], 5)


@pytest.mark.parametrize("body", [{"unexpected": True}, {"items": "nope"}, {"items": [{"nodomain": 1}]}])
def test_unexpected_shapes_become_gddy_error(body):
    client, _ = make_client(respond(body))

    with pytest.raises(GddyError):
        client.suggest("sunrisebakery", ["com"], 5)


def test_timeout_becomes_gddy_error():
    def timeout(request):
        raise httpx.ReadTimeout("slow")

    client, _ = make_client(timeout)

    with pytest.raises(GddyError):
        client.check_availability("achaar.com")


def test_token_is_not_logged(caplog):
    client, _ = make_client(respond({"name": "X"}, status=401))

    with caplog.at_level("DEBUG"), pytest.raises(GddyError):
        client.suggest("sunrisebakery", ["com"], 5)

    assert "secret-pat" not in caplog.text


@pytest.mark.parametrize("query", ["bad query", "a;b", "", "x" * 101, "-start"])
def test_unsafe_query_is_rejected_before_sending(query):
    client, requests = make_client(respond(SUGGESTIONS))

    with pytest.raises(GddyError):
        client.suggest(query, ["com"], 5)
    assert requests == []


@pytest.mark.parametrize("domain", ["nodot", "a b.com", "a.com;x", ""])
def test_unsafe_domain_is_rejected_before_sending(domain):
    client, requests = make_client(respond(availability(available=True)))

    with pytest.raises(GddyError):
        client.check_availability(domain)
    assert requests == []

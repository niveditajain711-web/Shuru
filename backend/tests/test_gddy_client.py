import json
from datetime import UTC, datetime

import httpx
import pytest

from app.clients.gddy_client import _to_amount, _to_offer, _to_quote
from app.core.errors import DomainTakenError, GddyError
from app.models import DomainOffer, PremiumFee
from app.schemas import gddy
from tests.helpers import QUOTE, make_client, make_locked_quote, respond

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





PREMIUM_FEE = {"type": "ONE_TIME_PREMIUM_DOMAIN_PURCHASE", "fee": {"currencyCode": "USD", "value": 390000}}


def test_suggested_premium_domain_carries_its_fee():
    premium = {"items": [{"domain": "premium.com", "prices": [{**one_year(), "fees": [PREMIUM_FEE]}]}]}
    client, _ = make_client(respond(premium))

    offer = client.suggest("premium", ["com"], 5)[0]

    assert offer.fees == [PremiumFee(type="ONE_TIME_PREMIUM_DOMAIN_PURCHASE", currency="USD", value=390000, amount=3900.0)]
    assert offer.price == 9.19  # the registration price alone; the fee is separate


def test_ordinary_domains_have_no_fees():
    client, _ = make_client(respond(SUGGESTIONS))

    assert client.suggest("sunrisebakery", ["com"], 5)[0].fees == []


def test_checked_premium_domain_carries_its_fee():
    reply = availability(available=True, prices=[{**one_year(), "fees": [PREMIUM_FEE]}])
    client, _ = make_client(respond(reply))

    offer = client.check_availability("achaar.com")

    assert offer.fees[0].amount == 3900.0


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


def test_quote_is_parsed_with_price_in_major_units():
    client, requests = make_client(respond(QUOTE))

    quote = client.quote_registration("achaar.com")

    assert (quote.price, quote.renewal_price, quote.currency, quote.token) == (9.19, 11.59, "USD", "tok-1")
    assert quote.agreements[0].type == "API_DPA"
    assert json.loads(requests[0].content) == {"domain": "achaar.com", "period": 1}
    assert requests[0].url.path == "/v3/domains/registration-quotes"


def test_quote_keeps_premium_fees_verbatim():
    premium = {**QUOTE, "fees": [{"type": "ONE_TIME_PREMIUM_DOMAIN_PURCHASE", "fee": {"currencyCode": "USD", "value": 390000}}]}
    client, _ = make_client(respond(premium))

    fee = client.quote_registration("achaar.com").fees[0]

    assert (fee.value, fee.amount) == (390000, 3900.0)


def test_unavailable_or_registered_domain_is_taken():
    client, _ = make_client(respond({"domain": "achaar.com", "available": False}))
    with pytest.raises(DomainTakenError):
        client.quote_registration("achaar.com")

    client, _ = make_client(respond({}, status=409))
    with pytest.raises(DomainTakenError):
        client.quote_registration("achaar.com")


def test_incomplete_quote_is_an_error():
    client, _ = make_client(respond({**QUOTE, "requiredAgreements": []}))

    with pytest.raises(GddyError):
        client.quote_registration("achaar.com")


def test_register_sends_token_consent_and_idempotency_key():
    client, requests = make_client(respond({"registrationId": "reg-9", "status": "CONFIRMED"}, status=202))
    agreed_at = datetime(2030, 1, 1, 10, 0, tzinfo=UTC)

    result = client.register(make_locked_quote(), agreed_at)

    assert result == ("reg-9", "CONFIRMED")
    request = requests[0]
    assert request.method == "POST" and request.url.path == "/v3/domains/registrations"
    assert request.headers["Idempotency-Key"] == "key-1"
    assert json.loads(request.content) == {
        "quoteToken": "tok-1",
        "domain": "achaar.com",
        "period": 1,
        "consent": {"agreedAt": "2030-01-01T10:00:00Z", "agreementTypes": ["API_DPA"]},
    }


def test_register_echoes_acknowledged_fees_verbatim():
    client, requests = make_client(respond({"registrationId": "r", "status": "CONFIRMED"}, status=202))
    fee = PremiumFee(type="ONE_TIME_PREMIUM_DOMAIN_PURCHASE", currency="USD", value=390000, amount=3900.0)

    client.register(make_locked_quote(fees=[fee]), datetime.now(UTC))

    consent = json.loads(requests[0].content)["consent"]
    assert consent["acknowledgedFees"] == [
        {"type": "ONE_TIME_PREMIUM_DOMAIN_PURCHASE", "fee": {"currencyCode": "USD", "value": 390000}}
    ]


def test_get_registration_reads_status():
    client, requests = make_client(respond({"registrationId": "reg-9", "status": "COMPLETED", "expiresAt": "2031-01-01T00:00:00Z"}))

    status, expires_at = client.get_registration("reg-9")

    assert status == "COMPLETED" and expires_at.year == 2031
    assert requests[0].url.path == "/v3/domains/registrations/reg-9"


def test_registration_id_is_validated_before_it_goes_in_a_path():
    client, requests = make_client(respond({}))

    with pytest.raises(GddyError):
        client.get_registration("../domain-names")

    assert requests == []


@pytest.mark.parametrize(
    ("currency", "value", "expected"),
    [("USD", 919, 9.19), ("JPY", 1000, 1000.0), ("KWD", 12345, 12.345), ("usd", 5, 0.05)],
)
def test_amounts_use_the_currencys_decimals(currency, value, expected):
    assert _to_amount(gddy.Money(currencyCode=currency, value=value)) == expected


def test_offer_needs_a_one_year_price_and_a_valid_name():
    two_years = gddy.TermPrice(term="YEAR", period=2, price=gddy.Money(currencyCode="USD", value=100))

    assert _to_offer("achaar.com", [two_years]) is None
    assert _to_offer("achaar.com", []) is None


def parsed_quote(**changes):
    return gddy.RegistrationQuote.model_validate({**QUOTE, **changes})


def test_quote_mapping_rejects_incomplete_or_different_quotes():
    assert _to_quote(parsed_quote(), "achaar.com", 1) is not None
    assert _to_quote(parsed_quote(quoteToken=None), "achaar.com", 1) is None
    assert _to_quote(parsed_quote(price=None), "achaar.com", 1) is None
    assert _to_quote(parsed_quote(), "other.com", 1) is None
    assert _to_quote(parsed_quote(period=2), "achaar.com", 1) is None

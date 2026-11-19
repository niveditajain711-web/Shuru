import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from app.core.errors import (
    ConfirmationMismatchError,
    DomainTakenError,
    GddyError,
    InvalidRunStateError,
    PurchaseFailedError,
    QuoteExpiredError,
)
from app.models import Lang, PurchaseRequest, Quote, QuoteFee, RunState
from app.repositories.run_store import RunStore
from tests.test_gddy_client import make_client, respond
from tests.test_orchestrator import prepare_site

ACCEPT = PurchaseRequest(agreement_types=["API_DPA"], price=12.0)


def quoted(orchestrator):
    run = prepare_site(orchestrator)
    orchestrator.quote_purchase(run.id)
    return run


# --- Orchestrator: demo mode ---


def test_demo_purchase_never_calls_registrations(orchestrator, gddy):
    run = quoted(orchestrator)

    done = orchestrator.purchase(run.id, ACCEPT)

    assert done.state == RunState.PURCHASED
    assert done.purchase.demo is True
    assert done.purchase.registration_id is None
    assert gddy.calls == ["quote"]  # the quote is real, the registration is skipped


def test_quote_is_marked_as_demo(orchestrator):
    run = prepare_site(orchestrator)

    assert orchestrator.quote_purchase(run.id).quote.demo is True


def test_quote_token_is_not_sent_to_the_browser_but_is_stored(orchestrator, tmp_path):
    run = prepare_site(orchestrator)
    orchestrator.quote_purchase(run.id)

    shown = orchestrator.get_run(run.id).model_dump(mode="json")
    assert "token" not in shown["quote"] and "idempotency_key" not in shown["quote"]
    assert orchestrator.get_run(run.id).quote.token == "secret-token"


def test_cannot_quote_or_buy_before_the_site_exists(orchestrator):
    run = orchestrator.create_run("pickles", Lang.EN)

    with pytest.raises(InvalidRunStateError):
        orchestrator.quote_purchase(run.id)
    with pytest.raises(InvalidRunStateError):
        orchestrator.purchase(run.id, ACCEPT)


def test_cannot_buy_without_a_quote(orchestrator):
    run = prepare_site(orchestrator)

    with pytest.raises(InvalidRunStateError):
        orchestrator.purchase(run.id, ACCEPT)


@pytest.mark.parametrize(
    "request_",
    [
        PurchaseRequest(agreement_types=["OTHER"], price=12.0),
        PurchaseRequest(agreement_types=["API_DPA"], price=1.0),
    ],
)
def test_purchase_rejects_what_the_user_did_not_accept(orchestrator, request_):
    run = quoted(orchestrator)

    with pytest.raises(ConfirmationMismatchError):
        orchestrator.purchase(run.id, request_)

    assert orchestrator.get_run(run.id).state == RunState.SITE_GENERATED


def test_premium_fees_must_be_acknowledged(orchestrator, gddy):
    gddy.fees = [QuoteFee(type="ONE_TIME_PREMIUM_DOMAIN_PURCHASE", currency="USD", value=390000, amount=3900.0)]
    run = quoted(orchestrator)

    with pytest.raises(ConfirmationMismatchError):
        orchestrator.purchase(run.id, ACCEPT)
    done = orchestrator.purchase(run.id, ACCEPT.model_copy(update={"acknowledged_fees": True}))

    assert done.state == RunState.PURCHASED


def test_expired_quote_cannot_be_used(orchestrator, gddy):
    gddy.expires_in = timedelta(seconds=-1)
    run = quoted(orchestrator)

    with pytest.raises(QuoteExpiredError):
        orchestrator.purchase(run.id, ACCEPT)


def test_taken_domain_cannot_be_quoted(orchestrator, gddy, monkeypatch):
    run = prepare_site(orchestrator)
    monkeypatch.setattr(gddy, "quote_registration", lambda *a, **k: (_ for _ in ()).throw(DomainTakenError()))

    with pytest.raises(DomainTakenError):
        orchestrator.quote_purchase(run.id)


def test_preview_still_works_after_purchase(orchestrator):
    run = quoted(orchestrator)
    orchestrator.purchase(run.id, ACCEPT)

    assert "<html" in orchestrator.render_preview(run.id, Lang.EN)


# --- Orchestrator: real mode (GoDaddy is faked, so nothing is bought) ---


@pytest.fixture
def real_mode_orchestrator(tmp_path, claude, domains, gddy):
    from app.core.config import Settings
    from app.services.orchestrator import Orchestrator
    from app.services.purchase_service import PurchaseService
    from app.services.site_service import SiteService

    settings = Settings(demo_mode=False, purchase_poll_seconds=0, purchase_poll_interval_seconds=0)
    return Orchestrator(
        store=RunStore(tmp_path / "real.sqlite"),
        claude=claude,
        domains=domains,
        sites=SiteService(),
        purchases=PurchaseService(gddy, settings),
        settings=settings,
    )


def test_real_purchase_registers_once(real_mode_orchestrator, gddy):
    run = quoted(real_mode_orchestrator)

    done = real_mode_orchestrator.purchase(run.id, ACCEPT)

    assert done.state == RunState.PURCHASED
    assert done.purchase.demo is False
    assert done.purchase.registration_id == "reg-1"
    assert gddy.calls.count("register") == 1


def test_pending_registration_is_checked_not_repeated(real_mode_orchestrator, gddy):
    gddy.registration_status = "EXECUTING"
    run = quoted(real_mode_orchestrator)

    pending = real_mode_orchestrator.purchase(run.id, ACCEPT)
    assert pending.state == RunState.PURCHASING
    assert pending.purchase.status == "pending"

    gddy.statuses = ["COMPLETED"]
    done = real_mode_orchestrator.refresh_purchase(run.id)

    assert done.state == RunState.PURCHASED
    assert gddy.calls.count("register") == 1  # the second call only polled


def test_failed_registration_discards_the_quote(real_mode_orchestrator, gddy):
    gddy.registration_status = "FAILED"
    run = quoted(real_mode_orchestrator)

    with pytest.raises(PurchaseFailedError):
        real_mode_orchestrator.purchase(run.id, ACCEPT)

    after = real_mode_orchestrator.get_run(run.id)
    assert after.state == RunState.SITE_GENERATED
    assert after.quote is None


# --- Store ---


def test_store_round_trips_quote_and_purchase(orchestrator):
    run = quoted(orchestrator)
    done = orchestrator.purchase(run.id, ACCEPT)

    assert orchestrator.get_run(run.id) == done


def test_store_adds_purchase_columns_to_an_old_database(tmp_path):
    import sqlite3

    path = tmp_path / "old.sqlite"
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE runs (id TEXT PRIMARY KEY, state TEXT NOT NULL, lang TEXT NOT NULL, idea TEXT NOT NULL, "
        "brief TEXT NOT NULL, domains TEXT NOT NULL, domain TEXT, site TEXT, regenerations INTEGER NOT NULL, "
        "created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"
    )
    conn.commit()
    conn.close()

    RunStore(path)  # must not raise, and must add the columns

    cols = {row[1] for row in sqlite3.connect(path).execute("PRAGMA table_info(runs)")}
    assert {"quote", "purchase"} <= cols


# --- API ---


def test_purchase_flow_over_http(client):
    run_id = client.post("/api/runs", json={"idea": "pickles", "lang": "en"}).json()["id"]
    client.get(f"/api/runs/{run_id}/domains")
    client.post(f"/api/runs/{run_id}/domain", json={"domain": "achaar1.com"})
    client.post(f"/api/runs/{run_id}/generate", json={"domain": "achaar1.com", "price": 12.0})

    quote = client.post(f"/api/runs/{run_id}/quote").json()["quote"]
    assert quote["price"] == 12.0 and quote["demo"] is True
    assert quote["agreements"][0]["type"] == "API_DPA"
    assert "token" not in quote

    done = client.post(f"/api/runs/{run_id}/purchase", json={"agreement_types": ["API_DPA"], "price": 12.0}).json()
    assert done["state"] == "purchased"
    assert done["purchase"]["demo"] is True


def test_refresh_is_only_for_a_pending_purchase(orchestrator):
    run = quoted(orchestrator)

    with pytest.raises(InvalidRunStateError):
        orchestrator.refresh_purchase(run.id)


def test_purchase_out_of_order_returns_conflict(client):
    run_id = client.post("/api/runs", json={"idea": "pickles", "lang": "en"}).json()["id"]

    response = client.post(f"/api/runs/{run_id}/purchase", json={"agreement_types": ["API_DPA"], "price": 1.0})

    assert response.status_code == 409


def test_purchase_needs_an_accepted_agreement(client):
    response = client.post("/api/runs/x/purchase", json={"agreement_types": [], "price": 1.0})

    assert response.status_code == 422


# --- GddyClient: quote and registration ---

# The OpenAPI spec puts the price at the top level of the quote.
QUOTE = {
    "domain": "achaar.com",
    "available": True,
    "quoteToken": "tok-1",
    "expiresAt": "2030-01-01T10:10:00Z",
    "period": 1,
    "price": {"currencyCode": "USD", "value": 919},
    "renewalPrice": {"currencyCode": "USD", "value": 1159},
    "requiredAgreements": [{"agreementType": "API_DPA", "title": "Purchase Agreement", "url": "https://example.test/a"}],
}


def test_quote_is_parsed_with_price_in_major_units():
    client, requests = make_client(respond(QUOTE))

    quote = client.quote_registration("achaar.com")

    assert (quote.price, quote.renewal_price, quote.currency, quote.token) == (9.19, 11.59, "USD", "tok-1")
    assert quote.agreements[0].type == "API_DPA"
    assert quote.idempotency_key
    assert json.loads(requests[0].content) == {"domain": "achaar.com", "period": 1}
    assert requests[0].url.path == "/v3/domains/registration-quotes"


def test_quote_also_reads_the_guides_nested_items_shape():
    nested = {k: v for k, v in QUOTE.items() if k not in ("price", "renewalPrice")}
    nested["items"] = [{"domain": "achaar.com", "period": 1, "price": QUOTE["price"]}]
    client, _ = make_client(respond(nested))

    assert client.quote_registration("achaar.com").price == 9.19


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


def make_quote(**kw) -> Quote:
    base = dict(
        domain="achaar.com", period=1, price=9.19, currency="USD", token="tok-1", idempotency_key="key-1",
        agreements=[{"type": "API_DPA", "title": "T"}], expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )
    return Quote(**{**base, **kw})


def test_register_sends_token_consent_and_idempotency_key():
    client, requests = make_client(respond({"registrationId": "reg-9", "status": "CONFIRMED"}, status=202))
    agreed_at = datetime(2030, 1, 1, 10, 0, tzinfo=UTC)

    result = client.register(make_quote(), agreed_at)

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
    fee = QuoteFee(type="ONE_TIME_PREMIUM_DOMAIN_PURCHASE", currency="USD", value=390000, amount=3900.0)

    client.register(make_quote(fees=[fee]), datetime.now(UTC))

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

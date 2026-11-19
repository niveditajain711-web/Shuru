"""The purchase rules, in demo mode (the default): the quote is real, the registration is skipped."""

from datetime import timedelta

import pytest

from app.core.errors import (
    ConfirmationMismatchError,
    DomainTakenError,
    InvalidRunStateError,
    QuoteExpiredError,
)
from app.models import Lang, PremiumFee, RunState
from app.schemas import PurchaseRequest
from tests.helpers import ACCEPT, prepare_site, quoted


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


def test_the_stored_quote_keeps_its_secrets(orchestrator):
    run = prepare_site(orchestrator)
    orchestrator.quote_purchase(run.id)

    stored = orchestrator.get_run(run.id).quote
    assert stored.token == "secret-token" and stored.idempotency_key


def test_every_quote_gets_its_own_idempotency_key(orchestrator):
    run = prepare_site(orchestrator)

    first = orchestrator.quote_purchase(run.id).quote.idempotency_key
    second = orchestrator.quote_purchase(run.id).quote.idempotency_key

    assert first and second and first != second


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
    gddy.fees = [PremiumFee(type="ONE_TIME_PREMIUM_DOMAIN_PURCHASE", currency="USD", value=390000, amount=3900.0)]
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


def test_taken_domain_cannot_be_quoted(orchestrator, gddy):
    run = prepare_site(orchestrator)
    gddy.taken = True

    with pytest.raises(DomainTakenError):
        orchestrator.quote_purchase(run.id)


def test_preview_still_works_after_purchase(orchestrator):
    run = quoted(orchestrator)
    orchestrator.purchase(run.id, ACCEPT)

    assert "<html" in orchestrator.render_preview(run.id, Lang.EN)


def test_nothing_earlier_can_be_redone_after_the_purchase(orchestrator):
    run = quoted(orchestrator)
    orchestrator.purchase(run.id, ACCEPT)

    with pytest.raises(InvalidRunStateError):
        orchestrator.list_domains(run.id)
    with pytest.raises(InvalidRunStateError):
        orchestrator.choose_domain(run.id, "achaar1.com")
    with pytest.raises(InvalidRunStateError):
        orchestrator.generate_site(run.id, "achaar1.com", 12.0)
    with pytest.raises(InvalidRunStateError):
        orchestrator.regenerate_site(run.id)
    with pytest.raises(InvalidRunStateError):
        orchestrator.quote_purchase(run.id)
    with pytest.raises(InvalidRunStateError):
        orchestrator.purchase(run.id, ACCEPT)


def test_refresh_is_only_for_a_pending_purchase(orchestrator):
    run = quoted(orchestrator)

    with pytest.raises(InvalidRunStateError):
        orchestrator.refresh_purchase(run.id)


def test_store_round_trips_quote_and_purchase(orchestrator):
    run = quoted(orchestrator)
    done = orchestrator.purchase(run.id, ACCEPT)

    assert orchestrator.get_run(run.id) == done

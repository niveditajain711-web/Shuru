"""The purchase in real mode. GoDaddy is faked, so nothing is bought."""

import pytest

from app.core.errors import PurchaseFailedError
from app.models import RunState
from tests.helpers import ACCEPT, quoted


@pytest.fixture
def demo_mode() -> bool:
    return False


def test_real_purchase_registers_once(orchestrator, gddy):
    run = quoted(orchestrator)

    done = orchestrator.purchase(run.id, ACCEPT)

    assert done.state == RunState.PURCHASED
    assert done.purchase.demo is False
    assert done.purchase.registration_id == "reg-1"
    assert gddy.calls.count("register") == 1


def test_pending_registration_is_checked_not_repeated(orchestrator, gddy):
    gddy.registration_status = "EXECUTING"
    run = quoted(orchestrator)

    pending = orchestrator.purchase(run.id, ACCEPT)
    assert pending.state == RunState.PURCHASING
    assert pending.purchase.status == "pending"

    gddy.statuses = ["COMPLETED"]
    done = orchestrator.refresh_purchase(run.id)

    assert done.state == RunState.PURCHASED
    assert gddy.calls.count("register") == 1  # the second call only polled


def test_failed_registration_discards_the_quote(orchestrator, gddy):
    gddy.registration_status = "FAILED"
    run = quoted(orchestrator)

    with pytest.raises(PurchaseFailedError):
        orchestrator.purchase(run.id, ACCEPT)

    after = orchestrator.get_run(run.id)
    assert after.state == RunState.SITE_GENERATED
    assert after.quote is None

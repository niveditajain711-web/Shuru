from datetime import UTC, datetime

import pytest

from app.errors import RunNotFoundError
from app.models import DomainOffer, Lang, Run, RunState
from app.store import RunStore
from tests.conftest import make_brief, make_site


def make_run() -> Run:
    now = datetime.now(UTC)
    return Run(
        id="r1", state=RunState.BRIEFED, lang=Lang.HI, idea="idea", brief=make_brief(),
        created_at=now, updated_at=now,
    )


def test_round_trip_of_a_full_run(tmp_path):
    store = RunStore(tmp_path / "db.sqlite")
    run = make_run()
    run.domains = [DomainOffer(name="a.com", price=1.5, currency="USD")]
    run.domain = run.domains[0]
    run.site = make_site()
    run.state = RunState.SITE_GENERATED
    run.regenerations = 2
    store.save(run)

    assert store.get("r1") == run


def test_save_updates_existing_run(tmp_path):
    store = RunStore(tmp_path / "db.sqlite")
    run = make_run()
    store.save(run)
    run.state = RunState.DOMAINS_LISTED
    store.save(run)

    assert store.get("r1").state == RunState.DOMAINS_LISTED


def test_get_unknown_run_raises(tmp_path):
    with pytest.raises(RunNotFoundError):
        RunStore(tmp_path / "db.sqlite").get("missing")


def test_data_survives_a_new_store_instance(tmp_path):
    RunStore(tmp_path / "db.sqlite").save(make_run())

    assert RunStore(tmp_path / "db.sqlite").get("r1").idea == "idea"

import pytest

from app.core.errors import (
    ClaudeError,
    ConfirmationMismatchError,
    DomainNotAvailableError,
    DomainTakenError,
    GddyError,
    InvalidRunStateError,
    RegenerationLimitError,
)
from app.models import Lang, RunState
from tests.helpers import prepare_site


def test_create_run_stores_brief(orchestrator):
    run = orchestrator.create_run("pickles", Lang.EN)

    assert run.state == RunState.BRIEFED
    assert orchestrator.get_run(run.id) == run


def test_failed_brief_creates_no_run(orchestrator, claude):
    claude.fail = True

    with pytest.raises(ClaudeError):
        orchestrator.create_run("pickles", Lang.EN)


def test_list_domains_uses_brief_names_or_keyword(orchestrator, domains):
    run = orchestrator.create_run("pickles", Lang.EN)

    listed = orchestrator.list_domains(run.id)
    assert listed.state == RunState.DOMAINS_LISTED
    assert domains.last_names == run.brief.name_ideas

    orchestrator.list_domains(run.id, keyword="mykeyword")
    assert domains.last_names == ["mykeyword"]


def test_failed_domain_search_keeps_state(orchestrator, domains):
    run = orchestrator.create_run("pickles", Lang.EN)
    domains.fail = True

    with pytest.raises(GddyError):
        orchestrator.list_domains(run.id)

    assert orchestrator.get_run(run.id).state == RunState.BRIEFED


def test_cannot_choose_domain_before_listing(orchestrator):
    run = orchestrator.create_run("pickles", Lang.EN)

    with pytest.raises(InvalidRunStateError):
        orchestrator.choose_domain(run.id, "achaar1.com")


def test_cannot_choose_unlisted_domain(orchestrator):
    run = orchestrator.create_run("pickles", Lang.EN)
    orchestrator.list_domains(run.id)

    with pytest.raises(DomainNotAvailableError):
        orchestrator.choose_domain(run.id, "other.com")


def test_choose_domain_records_fresh_price_without_calling_claude(orchestrator, claude, domains):
    run = orchestrator.create_run("pickles", Lang.EN)
    orchestrator.list_domains(run.id)
    domains.fresh_price = 13.5

    chosen = orchestrator.choose_domain(run.id, "achaar1.com")

    assert chosen.state == RunState.DOMAIN_CHOSEN
    assert chosen.domain.name == "achaar1.com"
    assert chosen.domain.price == 13.5
    assert chosen.site is None
    assert claude.site_calls == 0


def test_taken_domain_cannot_be_chosen(orchestrator, domains, claude):
    run = orchestrator.create_run("pickles", Lang.EN)
    orchestrator.list_domains(run.id)
    domains.taken = True

    with pytest.raises(DomainTakenError):
        orchestrator.choose_domain(run.id, "achaar1.com")

    assert orchestrator.get_run(run.id).state == RunState.DOMAINS_LISTED
    assert claude.site_calls == 0


def test_user_can_change_their_mind_about_the_domain(orchestrator):
    run = orchestrator.create_run("pickles", Lang.EN)
    orchestrator.list_domains(run.id)
    orchestrator.choose_domain(run.id, "achaar1.com")

    relisted = orchestrator.list_domains(run.id)

    assert relisted.state == RunState.DOMAINS_LISTED
    assert relisted.domain is None


def test_generate_site_after_confirmation(orchestrator, claude):
    run = orchestrator.create_run("pickles", Lang.EN)
    orchestrator.list_domains(run.id)
    orchestrator.choose_domain(run.id, "achaar1.com")

    generated = orchestrator.generate_site(run.id, "achaar1.com", 12.0)

    assert generated.state == RunState.SITE_GENERATED
    assert generated.site is not None
    assert claude.site_calls == 1


def test_cannot_generate_before_choosing(orchestrator):
    run = orchestrator.create_run("pickles", Lang.EN)
    orchestrator.list_domains(run.id)

    with pytest.raises(InvalidRunStateError):
        orchestrator.generate_site(run.id, "achaar1.com", 12.0)


@pytest.mark.parametrize("domain, price", [("other.com", 12.0), ("achaar1.com", 11.0)])
def test_generate_rejects_a_confirmation_that_does_not_match(orchestrator, claude, domain, price):
    run = orchestrator.create_run("pickles", Lang.EN)
    orchestrator.list_domains(run.id)
    orchestrator.choose_domain(run.id, "achaar1.com")

    with pytest.raises(ConfirmationMismatchError):
        orchestrator.generate_site(run.id, domain, price)

    assert claude.site_calls == 0


def test_failed_site_generation_can_be_retried(orchestrator, claude):
    run = orchestrator.create_run("pickles", Lang.EN)
    orchestrator.list_domains(run.id)
    orchestrator.choose_domain(run.id, "achaar1.com")
    claude.fail = True

    with pytest.raises(ClaudeError):
        orchestrator.generate_site(run.id, "achaar1.com", 12.0)
    assert orchestrator.get_run(run.id).state == RunState.DOMAIN_CHOSEN

    claude.fail = False
    assert orchestrator.generate_site(run.id, "achaar1.com", 12.0).state == RunState.SITE_GENERATED


def test_regeneration_is_capped(orchestrator, claude):
    run = prepare_site(orchestrator)

    assert orchestrator.regenerate_site(run.id).regenerations == 1
    assert orchestrator.regenerate_site(run.id).regenerations == 2
    with pytest.raises(RegenerationLimitError):
        orchestrator.regenerate_site(run.id)
    assert claude.site_calls == 3  # first generation plus two regenerations


def test_preview_requires_a_site(orchestrator):
    run = orchestrator.create_run("pickles", Lang.EN)

    with pytest.raises(InvalidRunStateError):
        orchestrator.render_preview(run.id, Lang.EN)


def test_preview_renders_requested_language(orchestrator):
    run = prepare_site(orchestrator)

    html = orchestrator.render_preview(run.id, Lang.HI)

    assert 'lang="hi"' in html
    assert "Homemade achaar (hindi)" in html

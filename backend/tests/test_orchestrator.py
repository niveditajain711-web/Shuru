import pytest

from app.errors import (
    ClaudeError,
    DomainNotAvailableError,
    GddyError,
    InvalidRunStateError,
    RegenerationLimitError,
)
from app.models import Lang, RunState


def prepare_site(orchestrator):
    run = orchestrator.create_run("pickles", Lang.EN)
    orchestrator.list_domains(run.id)
    orchestrator.choose_domain(run.id, "achaar1.com")
    return run


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


def test_choose_domain_generates_site(orchestrator):
    run = orchestrator.create_run("pickles", Lang.EN)
    orchestrator.list_domains(run.id)

    chosen = orchestrator.choose_domain(run.id, "achaar1.com")

    assert chosen.state == RunState.SITE_GENERATED
    assert chosen.domain.name == "achaar1.com"
    assert chosen.site is not None


def test_failed_site_generation_can_be_retried(orchestrator, claude):
    run = orchestrator.create_run("pickles", Lang.EN)
    orchestrator.list_domains(run.id)
    claude.fail = True

    with pytest.raises(ClaudeError):
        orchestrator.choose_domain(run.id, "achaar1.com")
    assert orchestrator.get_run(run.id).state == RunState.DOMAIN_CHOSEN

    claude.fail = False
    assert orchestrator.choose_domain(run.id, "achaar1.com").state == RunState.SITE_GENERATED


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

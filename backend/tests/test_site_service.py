from app.models import Lang
from app.services.site_service import SiteService
from tests.conftest import make_site


def test_renders_the_requested_language():
    html = SiteService().render(make_site(), "achaar.com", Lang.HI)

    assert '<html lang="hi">' in html
    assert "Homemade achaar (hindi)" in html
    assert "achaar.com" in html


def test_claude_text_is_escaped():
    site = make_site()
    site.hero.headline.en = '<script>alert("x")</script>'

    html = SiteService().render(site, "achaar.com", Lang.EN)

    assert "<script>" not in html
    assert "&lt;script&gt;" in html

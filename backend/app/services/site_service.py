from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.models import Lang, SiteContent

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


class SiteService:
    """Renders site content through the fixed template. The template owns all HTML and CSS."""

    def __init__(self) -> None:
        # Autoescape is always on: Claude output is untrusted and must never become markup.
        self._env = Environment(
            loader=FileSystemLoader(_TEMPLATES_DIR),
            autoescape=select_autoescape(default=True),
        )

    def render(self, site: SiteContent, domain: str, lang: Lang) -> str:
        return self._env.get_template("site.html").render(site=site.model_dump(), domain=domain, lang=lang.value)

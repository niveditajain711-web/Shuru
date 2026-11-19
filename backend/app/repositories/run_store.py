import contextlib
import logging
import sqlite3
from collections.abc import Iterator
from pathlib import Path

from pydantic import TypeAdapter

from app.core.errors import RunNotFoundError
from app.models import Brief, DomainOffer, LockedQuote, Purchase, Run, SiteContent

logger = logging.getLogger(__name__)

_DOMAINS = TypeAdapter(list[DomainOffer])

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    state TEXT NOT NULL,
    lang TEXT NOT NULL,
    idea TEXT NOT NULL,
    brief TEXT NOT NULL,
    domains TEXT NOT NULL,
    domain TEXT,
    site TEXT,
    quote TEXT,
    purchase TEXT,
    regenerations INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""


class RunStore:
    """Persists runs in a single SQLite file. Nested values are stored as JSON text."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(_SCHEMA)
            # Databases created before the purchase flow lack these columns.
            existing = {row["name"] for row in conn.execute("PRAGMA table_info(runs)")}
            for column in ("quote", "purchase"):
                if column not in existing:
                    conn.execute(f"ALTER TABLE runs ADD COLUMN {column} TEXT")

    @contextlib.contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        """Open a short-lived connection, committing on success and rolling back on error."""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def save(self, run: Run) -> None:
        """Insert the run, or update it if it already exists."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO runs (id, state, lang, idea, brief, domains, domain, site, quote, purchase,
                                  regenerations, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    state=excluded.state, domains=excluded.domains, domain=excluded.domain,
                    site=excluded.site, quote=excluded.quote, purchase=excluded.purchase,
                    regenerations=excluded.regenerations,
                    updated_at=excluded.updated_at
                """,
                (
                    run.id,
                    run.state.value,
                    run.lang.value,
                    run.idea,
                    run.brief.model_dump_json(),
                    _DOMAINS.dump_json(run.domains).decode(),
                    run.domain.model_dump_json() if run.domain else None,
                    run.site.model_dump_json() if run.site else None,
                    run.quote.model_dump_json() if run.quote else None,
                    run.purchase.model_dump_json() if run.purchase else None,
                    run.regenerations,
                    run.created_at.isoformat(),
                    run.updated_at.isoformat(),
                ),
            )
        logger.info("run saved run_id=%s state=%s", run.id, run.state.value)

    def get(self, run_id: str) -> Run:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        if row is None:
            raise RunNotFoundError(run_id)
        return Run(
            id=row["id"],
            state=row["state"],
            lang=row["lang"],
            idea=row["idea"],
            brief=Brief.model_validate_json(row["brief"]),
            domains=_DOMAINS.validate_json(row["domains"]),
            domain=DomainOffer.model_validate_json(row["domain"]) if row["domain"] else None,
            site=SiteContent.model_validate_json(row["site"]) if row["site"] else None,
            quote=LockedQuote.model_validate_json(row["quote"]) if row["quote"] else None,
            purchase=Purchase.model_validate_json(row["purchase"]) if row["purchase"] else None,
            regenerations=row["regenerations"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


import json
import logging
import re
import subprocess
import time
from collections.abc import Sequence

from pydantic import BaseModel, ValidationError

from app.errors import GddyError
from app.models import DOMAIN_LABEL_PATTERN, DOMAIN_PATTERN, DomainOffer

logger = logging.getLogger(__name__)


class _Suggestion(BaseModel):
    domain: str


class _Availability(BaseModel):
    domain: str
    available: bool
    price: float | None = None
    currency: str | None = None


class GddyClient:
    """The only module that runs the `gddy` CLI.

    Arguments are always passed as a list (never a shell string) and validated first, so user
    input cannot inject commands. Every call has a timeout, and every failure becomes `GddyError`.

    NOTE: the shape of `gddy`'s JSON output is not documented. `_Suggestion` and `_Availability`
    describe the shape assumed here and must be checked with `gddy domain suggest --schema` and
    `gddy domain available --schema` before relying on this module against a real account.
    """

    def __init__(self, binary: str, env: str, timeout_seconds: float) -> None:
        self._binary = binary
        self._env = env
        self._timeout = timeout_seconds

    def suggest(self, query: str, tlds: Sequence[str], limit: int) -> list[str]:
        """Return suggested domain names for a single-word query."""
        _require(re.fullmatch(DOMAIN_LABEL_PATTERN, query), "query")
        output = self._run(["domain", "suggest", query, "--tlds", ",".join(tlds), "--limit", str(limit)])
        try:
            return [_Suggestion.model_validate(item).domain for item in output]
        except (ValidationError, TypeError) as exc:
            logger.error("gddy unexpected suggest output=%r error=%s", output, exc)
            raise GddyError() from exc

    def check_availability(self, domain: str) -> DomainOffer | None:
        """Return the domain with its price if it can be registered, otherwise None."""
        _require(re.fullmatch(DOMAIN_PATTERN, domain), "domain")
        output = self._run(["domain", "available", domain])
        try:
            result = _Availability.model_validate(output)
        except ValidationError as exc:
            logger.error("gddy unexpected available output=%r error=%s", output, exc)
            raise GddyError() from exc
        if not result.available:
            return None
        if result.price is None or result.currency is None:
            logger.error("gddy available domain has no price domain=%s", domain)
            raise GddyError()
        return DomainOffer(name=result.domain, price=result.price, currency=result.currency)

    def _run(self, args: list[str]) -> object:
        command = [self._binary, *args, "--json", "--env", self._env]
        started = time.monotonic()
        try:
            proc = subprocess.run(command, capture_output=True, text=True, timeout=self._timeout, check=False)
        except subprocess.TimeoutExpired as exc:
            logger.error("gddy timeout command=%s timeout=%ss", command, self._timeout)
            raise GddyError() from exc
        except OSError as exc:
            logger.error("gddy could not start command=%s error=%r", command, exc)
            raise GddyError() from exc

        logger.info(
            "gddy command=%s exit_code=%d duration=%.2fs", command, proc.returncode, time.monotonic() - started
        )
        if proc.returncode != 0:
            logger.error("gddy failed command=%s stderr=%s", command, proc.stderr.strip())
            raise GddyError()
        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            logger.error("gddy returned invalid JSON command=%s stdout=%s", command, proc.stdout[:500])
            raise GddyError() from exc


def _require(match: object, what: str) -> None:
    """Reject values that would not be safe or valid as a `gddy` argument."""
    if not match:
        logger.error("gddy rejected invalid %s", what)
        raise GddyError()

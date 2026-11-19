from enum import StrEnum
from typing import Annotated

from pydantic import StringConstraints

# Name ideas and keywords become GoDaddy search queries, so they are restricted to
# characters that are valid in a domain label.
DOMAIN_LABEL_PATTERN = r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$"
DOMAIN_PATTERN = r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)+$"

DomainLabel = Annotated[str, StringConstraints(pattern=DOMAIN_LABEL_PATTERN)]
DomainName = Annotated[str, StringConstraints(pattern=DOMAIN_PATTERN)]
NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class Lang(StrEnum):
    EN = "en"
    HI = "hi"


class RunState(StrEnum):
    BRIEFED = "briefed"
    DOMAINS_LISTED = "domains_listed"
    DOMAIN_CHOSEN = "domain_chosen"
    SITE_GENERATED = "site_generated"
    PURCHASING = "purchasing"  # registration accepted, GoDaddy has not finished it yet
    PURCHASED = "purchased"

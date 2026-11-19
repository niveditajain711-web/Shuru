from typing import Annotated

from pydantic import BaseModel, StringConstraints


class ContactRequest(BaseModel):
    """A contact-form message. `website` is a honeypot: real visitors never see or fill it."""

    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100, pattern=r"^[^\r\n]+$")]
    email: Annotated[str, StringConstraints(strip_whitespace=True, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")]
    message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)]
    website: Annotated[str, StringConstraints(max_length=200)] = ""


class ContactResponse(BaseModel):
    ok: bool = True

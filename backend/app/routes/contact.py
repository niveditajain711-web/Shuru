from fastapi import APIRouter, Request

from app.core.errors import RateLimitedError
from app.models import ContactRequest, ContactResponse
from app.routes.deps import LimiterDep, MailerDep, client_key

router = APIRouter()


@router.post("/contact", response_model=ContactResponse)
def send_contact(body: ContactRequest, request: Request, mailer: MailerDep, limiter: LimiterDep) -> ContactResponse:
    if body.website:
        # Honeypot filled in: a bot. Pretend it worked, send nothing.
        return ContactResponse()
    if not limiter.allow(client_key(request)):
        raise RateLimitedError()
    mailer.send_contact(body.name, body.email, body.message)
    return ContactResponse()

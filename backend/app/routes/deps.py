from typing import Annotated

from fastapi import Depends, Request

from app.services.mail_service import MailService
from app.services.orchestrator import Orchestrator
from app.utils.rate_limit import RateLimiter


def get_orchestrator(request: Request) -> Orchestrator:
    return request.app.state.orchestrator


def get_mailer(request: Request) -> MailService:
    return request.app.state.mailer


def get_contact_limiter(request: Request) -> RateLimiter:
    return request.app.state.contact_limiter


def get_run_limiter(request: Request) -> RateLimiter:
    return request.app.state.run_limiter


def client_key(request: Request) -> str:
    """The key rate limits are counted by: the client IP (Caddy forwards the real one)."""
    return request.client.host if request.client else "unknown"


MailerDep = Annotated[MailService, Depends(get_mailer)]
LimiterDep = Annotated[RateLimiter, Depends(get_contact_limiter)]
RunLimiterDep = Annotated[RateLimiter, Depends(get_run_limiter)]
OrchestratorDep = Annotated[Orchestrator, Depends(get_orchestrator)]

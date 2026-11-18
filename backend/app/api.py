from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse

from app.errors import RateLimitedError
from app.models import (
    DOMAIN_LABEL_PATTERN,
    ChooseDomainRequest,
    ContactRequest,
    ContactResponse,
    CreateRunRequest,
    GenerateSiteRequest,
    Lang,
    Run,
)
from app.orchestrator import Orchestrator
from app.rate_limit import RateLimiter
from app.services.mail_service import MailService


def get_orchestrator(request: Request) -> Orchestrator:
    return request.app.state.orchestrator


def get_mailer(request: Request) -> MailService:
    return request.app.state.mailer


def get_contact_limiter(request: Request) -> RateLimiter:
    return request.app.state.contact_limiter


MailerDep = Annotated[MailService, Depends(get_mailer)]
LimiterDep = Annotated[RateLimiter, Depends(get_contact_limiter)]
OrchestratorDep = Annotated[Orchestrator, Depends(get_orchestrator)]

router = APIRouter(prefix="/api")


@router.post("/runs", response_model=Run, status_code=201)
def create_run(body: CreateRunRequest, orchestrator: OrchestratorDep) -> Run:
    return orchestrator.create_run(body.idea, body.lang)


@router.get("/runs/{run_id}", response_model=Run)
def get_run(run_id: str, orchestrator: OrchestratorDep) -> Run:
    return orchestrator.get_run(run_id)


@router.get("/runs/{run_id}/domains", response_model=Run)
def list_domains(
    run_id: str,
    orchestrator: OrchestratorDep,
    keyword: Annotated[str | None, Query(pattern=DOMAIN_LABEL_PATTERN)] = None,
) -> Run:
    return orchestrator.list_domains(run_id, keyword)


@router.post("/runs/{run_id}/domain", response_model=Run)
def choose_domain(run_id: str, body: ChooseDomainRequest, orchestrator: OrchestratorDep) -> Run:
    return orchestrator.choose_domain(run_id, body.domain)


@router.post("/runs/{run_id}/generate", response_model=Run)
def generate_site(run_id: str, body: GenerateSiteRequest, orchestrator: OrchestratorDep) -> Run:
    return orchestrator.generate_site(run_id, body.domain, body.price)


@router.post("/runs/{run_id}/regenerate", response_model=Run)
def regenerate_site(run_id: str, orchestrator: OrchestratorDep) -> Run:
    return orchestrator.regenerate_site(run_id)


@router.get("/runs/{run_id}/preview", response_class=HTMLResponse)
def preview(run_id: str, orchestrator: OrchestratorDep, lang: Lang = Lang.EN) -> str:
    return orchestrator.render_preview(run_id, lang)


@router.post("/contact", response_model=ContactResponse)
def send_contact(body: ContactRequest, request: Request, mailer: MailerDep, limiter: LimiterDep) -> ContactResponse:
    if body.website:
        # Honeypot filled in: a bot. Pretend it worked, send nothing.
        return ContactResponse()
    if not limiter.allow(request.client.host if request.client else "unknown"):
        raise RateLimitedError()
    mailer.send_contact(body.name, body.email, body.message)
    return ContactResponse()

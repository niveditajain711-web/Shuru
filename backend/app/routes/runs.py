from typing import Annotated

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse

from app.core.errors import RateLimitedError
from app.models import DOMAIN_LABEL_PATTERN, Lang, Run
from app.routes.deps import OrchestratorDep, RunLimiterDep, client_key
from app.schemas import ChooseDomainRequest, CreateRunRequest, GenerateSiteRequest, PurchaseRequest, RunResponse

router = APIRouter()


@router.post("/runs", response_model=RunResponse, status_code=201)
def create_run(body: CreateRunRequest, request: Request, orchestrator: OrchestratorDep, limiter: RunLimiterDep) -> Run:
    # Checked before the Claude call, so a blocked request costs nothing.
    if not limiter.allow(client_key(request)):
        raise RateLimitedError("You've started a few sites already. Please try again in a little while.")
    return orchestrator.create_run(body.idea, body.lang)


@router.get("/runs/{run_id}", response_model=RunResponse)
def get_run(run_id: str, orchestrator: OrchestratorDep) -> Run:
    return orchestrator.get_run(run_id)


@router.get("/runs/{run_id}/domains", response_model=RunResponse)
def list_domains(
    run_id: str,
    orchestrator: OrchestratorDep,
    keyword: Annotated[str | None, Query(pattern=DOMAIN_LABEL_PATTERN)] = None,
) -> Run:
    return orchestrator.list_domains(run_id, keyword)


@router.post("/runs/{run_id}/domain", response_model=RunResponse)
def choose_domain(run_id: str, body: ChooseDomainRequest, orchestrator: OrchestratorDep) -> Run:
    return orchestrator.choose_domain(run_id, body.domain)


@router.post("/runs/{run_id}/generate", response_model=RunResponse)
def generate_site(run_id: str, body: GenerateSiteRequest, orchestrator: OrchestratorDep) -> Run:
    return orchestrator.generate_site(run_id, body.domain, body.price)


@router.post("/runs/{run_id}/regenerate", response_model=RunResponse)
def regenerate_site(run_id: str, orchestrator: OrchestratorDep) -> Run:
    return orchestrator.regenerate_site(run_id)


@router.post("/runs/{run_id}/quote", response_model=RunResponse)
def quote_purchase(run_id: str, orchestrator: OrchestratorDep) -> Run:
    return orchestrator.quote_purchase(run_id)


@router.post("/runs/{run_id}/purchase", response_model=RunResponse)
def purchase(run_id: str, body: PurchaseRequest, orchestrator: OrchestratorDep) -> Run:
    return orchestrator.purchase(run_id, body)


@router.post("/runs/{run_id}/purchase/refresh", response_model=RunResponse)
def refresh_purchase(run_id: str, orchestrator: OrchestratorDep) -> Run:
    return orchestrator.refresh_purchase(run_id)


@router.get("/runs/{run_id}/preview", response_class=HTMLResponse)
def preview(run_id: str, orchestrator: OrchestratorDep, lang: Lang = Lang.EN) -> str:
    return orchestrator.render_preview(run_id, lang)

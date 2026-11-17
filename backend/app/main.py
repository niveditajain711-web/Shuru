import logging

import anthropic
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api import router
from app.config import Settings
from app.errors import AppError
from app.logging_config import setup_logging
from app.orchestrator import Orchestrator
from app.services.claude_service import ClaudeService
from app.services.domain_service import DomainService
from app.services.gddy_client import GddyClient
from app.services.site_service import SiteService
from app.store import RunStore

logger = logging.getLogger(__name__)


def build_orchestrator(settings: Settings) -> Orchestrator:
    """Wire the real services together."""
    return Orchestrator(
        store=RunStore(settings.db_path),
        claude=ClaudeService(anthropic.Anthropic(), settings),
        domains=DomainService(
            GddyClient(settings.gddy_read_base_url, settings.gddy_pat.get_secret_value(), settings.gddy_timeout_seconds)
        ),
        sites=SiteService(),
        settings=settings,
    )


def create_app(orchestrator: Orchestrator) -> FastAPI:
    app = FastAPI(title="Shuru")
    app.state.orchestrator = orchestrator
    app.include_router(router)
    app.add_exception_handler(AppError, _handle_app_error)
    app.add_exception_handler(Exception, _handle_unexpected_error)
    return app


def create_default_app() -> FastAPI:
    """Entry point for uvicorn: `uvicorn app.main:create_default_app --factory`."""
    # Load secrets (ANTHROPIC_API_KEY, GDDY_PAT) from backend/.env into the process environment,
    # where the Anthropic SDK and our settings read them. Real env vars take precedence.
    load_dotenv()
    settings = Settings()
    setup_logging(settings.log_level)
    if not settings.gddy_pat.get_secret_value():
        logger.warning("GDDY_PAT is not set; GoDaddy calls will fail")
    logger.info("GoDaddy read base url=%s", settings.gddy_read_base_url)
    return create_app(build_orchestrator(settings))


def _handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    logger.info("request failed path=%s code=%s", request.url.path, exc.code)
    return _error_response(exc.status_code, exc.code, exc.message)


def _handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled error path=%s", request.url.path, exc_info=exc)
    return _error_response(500, "internal_error", "Something went wrong on our side. Please try again.")


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": {"code": code, "message": message}})

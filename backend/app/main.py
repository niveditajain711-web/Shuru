import logging

import anthropic
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.routes import router
from app.core.config import Settings
from app.core.errors import AppError
from app.core.logging import setup_logging
from app.services.orchestrator import Orchestrator
from app.utils.rate_limit import RateLimiter
from app.services.claude_service import ClaudeService
from app.services.domain_service import DomainService
from app.clients.gddy_client import GddyClient
from app.services.mail_service import MailService
from app.services.site_service import SiteService
from app.repositories.run_store import RunStore

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


def create_app(
    orchestrator: Orchestrator, mailer: MailService, contact_limiter: RateLimiter, run_limiter: RateLimiter
) -> FastAPI:
    app = FastAPI(title="Shuru")
    app.state.orchestrator = orchestrator
    app.state.mailer = mailer
    app.state.contact_limiter = contact_limiter
    app.state.run_limiter = run_limiter
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
    if not (settings.smtp_user and settings.smtp_password.get_secret_value()):
        logger.warning("SHURU_SMTP_USER / SHURU_SMTP_PASSWORD are not set; the contact form will be unavailable")
    logger.info("GoDaddy read base url=%s", settings.gddy_read_base_url)
    return create_app(
        build_orchestrator(settings),
        MailService(settings),
        RateLimiter(settings.contact_rate_limit, settings.contact_rate_window_seconds),
        RateLimiter(settings.run_rate_limit, settings.run_rate_window_seconds),
    )


def _handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    logger.info("request failed path=%s code=%s", request.url.path, exc.code)
    return _error_response(exc.status_code, exc.code, exc.message)


def _handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled error path=%s", request.url.path, exc_info=exc)
    return _error_response(500, "internal_error", "Something went wrong on our side. Please try again.")


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": {"code": code, "message": message}})

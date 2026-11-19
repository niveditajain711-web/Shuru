import logging
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager

import anthropic
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.clients.gddy_client import GddyClient
from app.core.config import Settings
from app.core.errors import AppError
from app.core.logging import setup_logging
from app.repositories.run_store import RunStore
from app.routes import router
from app.services.claude_service import ClaudeService
from app.services.domain_service import DomainService
from app.services.mail_service import MailService
from app.services.orchestrator import Orchestrator
from app.services.purchase_service import PurchaseService
from app.services.site_service import SiteService
from app.utils.rate_limit import RateLimiter

logger = logging.getLogger(__name__)


def build_orchestrator(settings: Settings, gddy_http: httpx.Client) -> Orchestrator:
    """Wire the real services together. Both GoDaddy clients share one HTTP connection pool."""
    pat = settings.gddy_pat.get_secret_value()
    timeout = settings.gddy_timeout_seconds
    return Orchestrator(
        store=RunStore(settings.db_path),
        claude=ClaudeService(anthropic.Anthropic(), settings),
        domains=DomainService(GddyClient(settings.gddy_read_base_url, pat, timeout, http=gddy_http)),
        sites=SiteService(),
        purchases=PurchaseService(GddyClient(settings.gddy_purchase_base_url, pat, timeout, http=gddy_http), settings),
        regeneration_cap=settings.regeneration_cap,
    )


def create_app(
    orchestrator: Orchestrator,
    mailer: MailService,
    contact_limiter: RateLimiter,
    run_limiter: RateLimiter,
    lifespan: Callable[[FastAPI], AbstractAsyncContextManager[None]] | None = None,
) -> FastAPI:
    app = FastAPI(title="Shuru", lifespan=lifespan)
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
    logger.info("GoDaddy read base url=%s purchase base url=%s", settings.gddy_read_base_url, settings.gddy_purchase_base_url)
    if settings.demo_mode:
        logger.warning("SHURU_DEMO_MODE is on: purchases are simulated and nothing will be registered or charged")
    else:
        logger.warning("SHURU_DEMO_MODE is off: purchases REGISTER REAL DOMAINS and charge the GoDaddy account")
    gddy_http = httpx.Client(timeout=settings.gddy_timeout_seconds)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        gddy_http.close()

    return create_app(
        build_orchestrator(settings, gddy_http),
        MailService(settings),
        RateLimiter(settings.contact_rate_limit, settings.contact_rate_window_seconds),
        RateLimiter(settings.run_rate_limit, settings.run_rate_window_seconds),
        lifespan=lifespan,
    )


def _handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    logger.info("request failed path=%s code=%s", request.url.path, exc.code)
    return _error_response(exc.status_code, exc.code, exc.message)


def _handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled error path=%s", request.url.path, exc_info=exc)
    return _error_response(500, "internal_error", "Something went wrong on our side. Please try again.")


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": {"code": code, "message": message}})

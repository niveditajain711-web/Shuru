from fastapi import APIRouter

from app.routes import contact, runs

router = APIRouter(prefix="/api")
router.include_router(runs.router)
router.include_router(contact.router)

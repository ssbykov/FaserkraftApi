from fastapi import APIRouter

from app.core import settings

from .api_v1 import router as router_api_v1


router = APIRouter()
router.include_router(
    router=router_api_v1,
    prefix=settings.api.prefix,
)


@router.get("/health", status_code=200)
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "calendar-api"}

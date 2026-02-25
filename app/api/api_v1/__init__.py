from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer

from app.core import settings
from .auth import router as auth_router
from .users import router as users_router
from .products import router as products_router
from .processes import router as processes_router
from .products_steps import router as products_steps_router
from .day_plans import router as day_plans_router
from .employees import router as employees_router

http_bearer = HTTPBearer(auto_error=False)


router = APIRouter(
    prefix=settings.api.v1.prefix,
    dependencies=[Depends(http_bearer)],
)


router.include_router(router=auth_router)
router.include_router(router=users_router)
router.include_router(router=products_router)
router.include_router(router=processes_router)
router.include_router(router=products_steps_router)
router.include_router(router=day_plans_router)
router.include_router(router=employees_router)

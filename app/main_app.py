from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from starlette.staticfiles import StaticFiles

from app.admin.init_admin import init_admin
from app.api import router as api_router
from app.core.logger_init import init_logger
from app.database import db_helper


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await db_helper.synch_backups()
    admin = await init_admin(app)
    app.state.admin = admin
    yield
    await db_helper.dispose()


def init_main_app() -> FastAPI:
    main_app = FastAPI(
        lifespan=lifespan,
        default_response_class=ORJSONResponse,
    )
    init_logger()
    main_app.mount("/static", StaticFiles(directory="./static"), name="static")

    main_app.include_router(router=api_router)

    return main_app

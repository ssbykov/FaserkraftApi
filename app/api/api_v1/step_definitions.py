from typing import List, Annotated, Sequence

from fastapi import APIRouter, HTTPException, Depends
from starlette import status

from app.api.api_v1.fastapi_users import current_user
from app.core import settings
from app.database import StepDefinition
from app.database.crud.step_definitions import (
    StepDefinitionRepository,
    get_step_definition_repo,
)
from app.database.models import User
from app.database.schemas.step_definition import StepDefinitionRead

router = APIRouter(
    tags=["Step definitions"],
    prefix=settings.api.v1.step_definitions,
)
router.include_router(
    router,
)


@router.get(
    "/",
    response_model=List[StepDefinitionRead],
    status_code=status.HTTP_200_OK,
)
async def get_step_definitions(
    repo: Annotated[StepDefinitionRepository, Depends(get_step_definition_repo)],
    user: Annotated[User, Depends(current_user)],
) -> Sequence[StepDefinition]:
    try:
        return await repo.get_all()
    except HTTPException as exc:
        # пробрасываем 404 и другие осознанные HTTP-ошибки
        raise exc
    except Exception:
        # внутренняя ошибка без лишних деталей наружу
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка при получении продукта",
        )

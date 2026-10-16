from typing import List, Annotated, Sequence

from fastapi import APIRouter, HTTPException, Depends
from starlette import status

from app.api.api_v1.dependencies import get_current_employee
from app.core import settings
from app.database import StepDefinition
from app.database.crud.step_definitions import (
    StepDefinitionRepository,
    get_step_definition_repo,
)
from app.database.schemas.step_definition import StepDefinitionRead

router = APIRouter(
    tags=["Step definitions"],
    prefix=settings.api.v1.step_definitions,
)


@router.get(
    "/",
    response_model=List[StepDefinitionRead],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_employee)],
)
async def get_step_definitions(
    repo: Annotated[StepDefinitionRepository, Depends(get_step_definition_repo)],
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
            detail="Произошла внутренняя ошибка при получении определений этапов",
        )

from typing import List, Annotated, Sequence

from fastapi import APIRouter, HTTPException, Depends
from starlette import status

from app.api.api_v1.dependencies import get_current_employee
from app.core import settings
from app.database import Process
from app.database.crud.processes import ProcessRepository, get_process_repo
from app.database.schemas.detailed import ProcessRead

router = APIRouter(
    tags=["Processes"],
    prefix=settings.api.v1.processes,
)


@router.get(
    "/",
    response_model=List[ProcessRead],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_employee)],
)
async def get_processes(
    repo: Annotated[ProcessRepository, Depends(get_process_repo)],
) -> Sequence[Process]:
    try:
        return await repo.get_all()
    except HTTPException as exc:
        # пробрасываем 404 и другие осознанные HTTP-ошибки
        raise exc
    except Exception:
        # внутренняя ошибка без лишних деталей наружу
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка при получении списка процессов",
        )
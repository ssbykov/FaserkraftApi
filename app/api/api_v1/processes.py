from typing import List, Annotated, Sequence

from fastapi import APIRouter, HTTPException, Depends
from starlette import status

from app.api.api_v1.fastapi_users import current_user
from app.core import settings
from app.database import Process
from app.database.crud.processes import ProcessRepository, get_process_repo
from app.database.models import User
from app.database.schemas.process import ProcessRead

router = APIRouter(
    tags=["Processes"],
    prefix=settings.api.v1.processes,
)


@router.get(
    "/",
    response_model=List[ProcessRead],
    status_code=status.HTTP_200_OK,
)
async def get_processes(
    repo: Annotated[ProcessRepository, Depends(get_process_repo)],
    user: Annotated[User, Depends(current_user)],
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

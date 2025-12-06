from typing import List, Annotated

from fastapi import APIRouter, HTTPException, Depends
from starlette import status

from app.api.api_v1.fastapi_users import current_user
from app.core import settings
from app.database.crud.processes import ProcessRepository, get_process_repo
from app.database.models import User
from app.database.schemas.process import ProcessRead
from app.database.schemas.product import ProductRead

router = APIRouter(
    tags=["Processes"],
    prefix=settings.api.v1.processes,
)
router.include_router(
    router,
)


@router.get(
    "/",
    response_model=List[ProcessRead],
    status_code=status.HTTP_200_OK,
)
async def get_product(
    repo: Annotated[ProcessRepository, Depends(get_process_repo)],
    user: Annotated[User, Depends(current_user)],
) -> List[ProductRead]:
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

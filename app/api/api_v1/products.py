from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from starlette import status

from app.api.api_v1.fastapi_users import current_super_user
from app.core import settings
from app.database.crud.products import ProductRepository, get_product_repo
from app.database.models import User
from app.database.schemas.product import ProductRead, ProductCreate, ProductCreateOut

router = APIRouter(
    tags=["Products"],
    prefix=settings.api.v1.products,
)
router.include_router(
    router,
)


@router.post("/", response_model=ProductCreateOut, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_in: ProductCreate,
    repo: Annotated[ProductRepository, Depends(get_product_repo)],
    user: Annotated[User, Depends(current_super_user)],
) -> ProductCreateOut | str:
    try:
        product = await repo.create_product(product_in)
        return ProductCreateOut.model_validate(product)
    except IntegrityError as e:
        msg = str(e.orig)
        if (
            "violates foreign key constraint" in msg
            or "ForeignKeyViolationError" in msg
        ):
            raise HTTPException(
                status_code=422, detail="Указан несуществующий process_id"
            )
        elif "duplicate key value" in msg or "уже существует" in msg:
            raise HTTPException(
                status_code=409,
                detail="Продукт с таким серийным номером уже существует",
            )
        else:
            # Остальные ошибки целостности
            raise HTTPException(status_code=400, detail=f"Ошибка данных: {msg}")
    except Exception as e:
        # Прочие ошибки — 500 Internal Server Error
        raise HTTPException(status_code=500, detail=f"Произошла ошибка: {e}")


@router.get(
    "/{serial_number}", response_model=ProductRead, status_code=status.HTTP_200_OK
)
async def get_product(
    serial_number: str,
    repo: Annotated[ProductRepository, Depends(get_product_repo)],
    user: Annotated[User, Depends(current_super_user)],
):
    try:
        return await repo.get(serial_number)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Произошла ошибка: {e}")

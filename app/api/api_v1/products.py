from typing import Annotated

from fastapi import APIRouter, Depends
from starlette import status

from app.api.api_v1.fastapi_users import current_super_user
from app.core import settings
from app.database import Product
from app.database.crud.products import ProductRepository, get_product_repo
from app.database.models import User
from app.database.schemas.product import ProductRead, ProductCreate

router = APIRouter(
    tags=["Products"],
    prefix=settings.api.v1.products,
)
router.include_router(
    router,
)


@router.post("/", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_in: ProductCreate,
    repo: Annotated[ProductRepository, Depends(get_product_repo)],
    user: Annotated[User, Depends(current_super_user)],
) -> Product | str:
    try:
        product = await repo.create_product(product_in)
        return product
    except Exception as e:
        return f"Произошла ошибка: {e}"


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
        return f"Произошла ошибка: {e}"

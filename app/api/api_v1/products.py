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
) -> ProductCreateOut:
    try:
        product = await repo.create_product(product_in)
        return ProductCreateOut.model_validate(product)

    except IntegrityError as e:
        msg = str(e.orig)

        # FK на process_id
        if (
            "violates foreign key constraint" in msg
            or "ForeignKeyViolationError" in msg
            or "foreign key" in msg.lower()
        ):
            raise HTTPException(
                status_code=422,
                detail="Указан несуществующий process_id",
            )

        # уникальность по serial_number
        if (
            "duplicate key value" in msg
            or "уже существует" in msg
            or "unique constraint" in msg.lower()
        ):
            raise HTTPException(
                status_code=409,
                detail="Продукт с таким серийным номером уже существует",
            )

        # прочие ошибки целостности без утечки текста SQL
        raise HTTPException(
            status_code=400,
            detail="Ошибка целостности данных при создании продукта",
        )

    except ValueError as e:
        # например, если в repo.create_product ты явно кинул,
        # что процесс не найден
        raise HTTPException(status_code=422, detail=str(e))

    except HTTPException:
        # если repo сам кинул HTTPException — просто пробрасываем
        raise

    except Exception:
        # внутренняя ошибка без деталей наружу
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка при создании продукта",
        )


@router.get(
    "/{serial_number}",
    response_model=ProductRead,
    status_code=status.HTTP_200_OK,
)
async def get_product(
    serial_number: str,
    repo: Annotated[ProductRepository, Depends(get_product_repo)],
    # user: Annotated[User, Depends(current_super_user)],
) -> ProductRead:
    try:
        product = await repo.get(serial_number)
        return ProductRead.model_validate(product)
    except HTTPException as exc:
        # пробрасываем 404 и другие осознанные HTTP-ошибки
        raise exc
    except Exception:
        # внутренняя ошибка без лишних деталей наружу
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка при получении продукта",
        )

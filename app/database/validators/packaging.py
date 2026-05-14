from app.database.models import Packaging
from app.database.models.product import ProductStatus


def get_packaging_with_non_normal_products(
    packaging_list: list[Packaging],
) -> list[str]:
    return [
        pack.serial_number
        for pack in packaging_list
        if any(product.status != ProductStatus.normal for product in pack.products)
    ]
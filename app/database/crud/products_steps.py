from app.database import ProductStep
from app.database.crud.mixines import GetBackNextIdMixin


class ProductStepRepository(GetBackNextIdMixin[ProductStep]):
    model = ProductStep

from app.database.crud.mixines import GetBackNextIdMixin
from app.database.models import SizeType


class SizeTypeRepository(GetBackNextIdMixin[SizeType]):
    model = SizeType

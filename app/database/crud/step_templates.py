from app.database import StepTemplate
from app.database.crud.mixines import GetBackNextIdMixin


class StepTemplateRepository(GetBackNextIdMixin[StepTemplate]):
    model = StepTemplate

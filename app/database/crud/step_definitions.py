from app.database import StepDefinition
from app.database.crud.mixines import GetBackNextIdMixin


class StepDefinitionRepository(GetBackNextIdMixin[StepDefinition]):
    model = StepDefinition

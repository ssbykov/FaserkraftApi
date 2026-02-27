from app.database import StepDefinition, SessionDep
from app.database.crud.mixines import GetBackNextIdMixin


def get_step_definition_repo(session: SessionDep) -> "StepDefinitionRepository":
    return StepDefinitionRepository(session)


class StepDefinitionRepository(GetBackNextIdMixin[StepDefinition]):
    model = StepDefinition

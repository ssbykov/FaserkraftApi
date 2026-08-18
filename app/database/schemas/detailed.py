from typing import List

from app.database.schemas.process import ProcessBase, ProcessReadShort
from app.database.schemas.step_definition import StepDefinitionBase, StepDefinitionRead


class ProcessRead(ProcessReadShort):
    description: str | None = None
    steps: List[StepDefinitionRead]


class StepDefinitionReadWithProcess(StepDefinitionBase):
    work_process: ProcessBase

from app.database.crud.mixines import GetBackNextIdMixin
from app.database.models import DailyPlanStep


class DailyPlanStepRepository(GetBackNextIdMixin[DailyPlanStep]):
    model = DailyPlanStep

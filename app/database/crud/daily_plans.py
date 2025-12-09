from app.database import DailyPlan
from app.database.crud.mixines import GetBackNextIdMixin


class DailyPlanRepository(GetBackNextIdMixin[DailyPlan]):
    model = DailyPlan

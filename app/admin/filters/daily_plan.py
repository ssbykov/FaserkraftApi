from typing import Callable, Any

from sqlalchemy import select, Select
from starlette.requests import Request


class EmployeeFilter:
    """
    Кастомный фильтр для DailyPlan по сотруднику (через relationship employee).
    """

    def __init__(
        self,
        title: str = "Сотрудник",
        parameter_name: str = "employee_id",
    ):
        self.title = title
        self.parameter_name = parameter_name

    async def lookups(
        self, request: Request, model: Any, run_query: Callable[[Select], Any]
    ) -> list[tuple[str, str]]:
        from app.database import Employee  # импорт тут, чтобы избежать циклов

        stmt = select(Employee.id, Employee.name).distinct()
        rows = await run_query(stmt)
        return [("", "Все")] + [(str(emp_id), name) for emp_id, name in rows if name]

    async def get_filtered_query(self, query: Select, value: Any, model: Any) -> Select:
        if not value:
            return query

        from app.database import DailyPlan  # если нужно, но можно использовать model

        try:
            employee_id = int(value)
        except ValueError:
            return query

        return query.filter(DailyPlan.employee_id == employee_id)

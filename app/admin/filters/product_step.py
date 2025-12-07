from typing import Callable, Any, List, Tuple

from sqlalchemy import Select, select
from starlette.requests import Request


class ProductStepPerformerFilter:
    """
    Фильтр для ProductStep по сотруднику-исполнителю (performed_by).
    """

    def __init__(
        self,
        title: str = "Исполнитель",
        parameter_name: str = "performed_by_id",
    ):
        self.title = title
        self.parameter_name = parameter_name

    async def lookups(
        self, request: Request, model: Any, run_query: Callable[[Select], Any]
    ) -> List[Tuple[str, str]]:
        from app.database import Employee, ProductStep

        stmt = (
            select(Employee.id, Employee.name)  # имя/ФИО сотрудника
            .join(ProductStep, ProductStep.performed_by_id == Employee.id)
            .distinct()
        )
        rows = await run_query(stmt)

        choices: List[Tuple[str, str]] = [("", "All")]
        for emp_id, emp_name in rows:
            if emp_id is not None:
                choices.append((str(emp_id), emp_name or f"ID {emp_id}"))
        return choices

    async def get_filtered_query(self, query: Select, value: Any, model: Any) -> Select:
        if not value:
            return query

        from app.database import ProductStep

        try:
            employee_id = int(value)
        except (TypeError, ValueError):
            return query

        return query.filter(ProductStep.performed_by.has(id=employee_id))


class ProductStepStatusFilter:
    """
    Фильтр для ProductStep по статусу (Enum StepStatus).
    """

    def __init__(
        self,
        title: str = "Статус этапа",
        parameter_name: str = "status",
    ):
        self.title = title
        self.parameter_name = parameter_name

    async def lookups(
        self, request: Request, model: Any, run_query: Callable[[Select], Any]
    ) -> List[Tuple[str, str]]:
        from app.database.models import ProductStep
        from app.database.models.product_step import StepStatus

        # Берём реально используемые значения статуса из БД
        stmt = select(ProductStep.status).distinct()
        rows = await run_query(stmt)

        used_statuses: set[StepStatus] = {row[0] for row in rows if row[0] is not None}

        choices: List[Tuple[str, str]] = [("", "All")]
        for status in StepStatus:
            if status in used_statuses:
                # в query‑параметре отправляем name, а не value, чтобы было стабильнее
                choices.append((status.name, status.name))
        return choices

    async def get_filtered_query(self, query: Select, value: Any, model: Any) -> Select:
        if not value:
            return query

        from app.database import ProductStep
        from app.database.models.product_step import StepStatus

        try:
            status = StepStatus[value]  # конвертация из строки name -> Enum
        except KeyError:
            return query

        return query.filter(ProductStep.status == status)

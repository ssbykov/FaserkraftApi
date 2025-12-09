from typing import Callable, Any, List, Tuple

from sqlalchemy import select, Select
from starlette.requests import Request


class ProcessNameFilter:
    """
    Кастомный фильтр для фильтрации продуктов по названию процесса через relationship.
    """

    def __init__(
        self,
        title: str = "Техпроцесс",
        parameter_name: str = "process_name",
    ):
        self.title = title
        self.parameter_name = parameter_name

    async def lookups(
        self, request: Request, model: Any, run_query: Callable[[Select], Any]
    ) -> List[Tuple[str, str]]:
        from app.database import Process  # Импортируйте здесь, чтобы избежать циклов

        stmt = select(Process.name).distinct()
        names = [row[0] for row in await run_query(stmt)]
        return [("", "All")] + [(name, name) for name in names if name]

    async def get_filtered_query(self, query: Select, value: Any, model: Any) -> Select:
        if not value:
            return query
        from app.database import Product  # Импортируйте здесь, чтобы избежать циклов

        return query.filter(Product.work_process.has(name=value))

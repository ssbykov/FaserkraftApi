from collections import defaultdict

from sqlalchemy import select

from app.database import EmployeeNormCalculation, SessionDep
from app.database.crud.mixines import GetBackNextIdMixin


def get_employee_norm_calculation_repo(
    session: SessionDep,
) -> "EmployeeNormCalculationRepository":
    return EmployeeNormCalculationRepository(session)


class EmployeeNormCalculationRepository(GetBackNextIdMixin[EmployeeNormCalculation]):
    model = EmployeeNormCalculation

    async def get_norms_for_steps(
        self,
        step_definition_ids: set[int],
    ) -> dict[int, list[EmployeeNormCalculation]]:
        """
        Возвращает по каждому step_definition_id список записей норм,
        отсортированный по дате (для построения интервалов действия нормы
        в app.services.norm_calculation.build_norm_intervals).
        """
        if not step_definition_ids:
            return {}

        stmt = (
            select(EmployeeNormCalculation)
            .where(EmployeeNormCalculation.step_definition_id.in_(step_definition_ids))
            .order_by(
                EmployeeNormCalculation.step_definition_id,
                EmployeeNormCalculation.date,
            )
        )
        result = await self.session.execute(stmt)
        rows = result.scalars().all()

        grouped: dict[int, list[EmployeeNormCalculation]] = defaultdict(list)
        for row in rows:
            grouped[row.step_definition_id].append(row)
        return grouped
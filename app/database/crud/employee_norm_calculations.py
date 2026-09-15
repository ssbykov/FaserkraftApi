from app.database import SessionDep
from app.database.crud.mixines import GetBackNextIdMixin
from app.database.models import EmployeeNormCalculation


def get_employee_norm_calculation_repo(
    session: SessionDep,
) -> "EmployeeNormCalculationRepository":
    return EmployeeNormCalculationRepository(session)


class EmployeeNormCalculationRepository(GetBackNextIdMixin[EmployeeNormCalculation]):
    model = EmployeeNormCalculation

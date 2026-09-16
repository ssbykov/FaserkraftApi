from app.admin.custom_model_view import CustomModelView
from app.database.models import EmployeeNormCalculation
from app.database.crud.employee_norm_calculations import EmployeeNormCalculationRepository


class EmployeeNormCalculationAdmin(
    CustomModelView[EmployeeNormCalculation],
    model=EmployeeNormCalculation,
):
    repo_type = EmployeeNormCalculationRepository
    name_plural = "Расчеты норм выработки"
    name = "Расчет нормы выработки"
    category = "Раздел процессов"

    column_labels = {
        EmployeeNormCalculation.step_definition: "Этап",
        EmployeeNormCalculation.date: "Дата",
        EmployeeNormCalculation.salary_rate: "Расчетный оклад",
        EmployeeNormCalculation.difficulty_coefficient: "Коэффициент сложности",
        EmployeeNormCalculation.daily_norm: "Дневная норма",
    }

    column_list = (
        "step_definition",
        "date",
        "salary_rate",
        "difficulty_coefficient",
        "daily_norm",
    )

    column_details_list = (
        "step_definition",
        "date",
        "salary_rate",
        "difficulty_coefficient",
        "daily_norm",
    )

    form_args = {
        "step_definition": {
            "label": "Этап",
        }
    }

    form_columns = [
        EmployeeNormCalculation.step_definition,
        EmployeeNormCalculation.date,
        EmployeeNormCalculation.salary_rate,
        EmployeeNormCalculation.difficulty_coefficient,
        EmployeeNormCalculation.daily_norm,
    ]

    can_edit = True
    can_delete = True
    can_export = False
from typing import Any

from sqladmin._queries import Query
from sqlalchemy.orm import selectinload
from starlette.requests import Request
from wtforms import Form, SelectField, IntegerField, DateField, FieldList, FormField
from wtforms.validators import DataRequired, NumberRange, Optional

from app.admin.custom_model_view import CustomModelView
from app.admin.filters.daily_plan import EmployeeFilter
from app.database import DailyPlan
from app.database.crud.daily_plans import DailyPlanRepository
from app.database.models import DailyPlanStep


class DailyPlanStepForm(Form):
    process_id = SelectField("Процесс", coerce=int, validators=[DataRequired()])
    step_definition_id = SelectField("Этап", coerce=int, validators=[DataRequired()])
    planned_quantity = IntegerField(
        "План, шт.", validators=[DataRequired(), NumberRange(min=0)]
    )
    actual_quantity = IntegerField(
        "Факт, шт.",
        validators=[Optional(), NumberRange(min=0)],
        default=0,
    )


class DailyPlanForm(Form):
    employee_id = SelectField("Сотрудник", coerce=int, validators=[DataRequired()])
    date = DateField("Дата", validators=[DataRequired()])

    steps = FieldList(FormField(DailyPlanStepForm), min_entries=0)


class DailyPlanQuery(Query):
    async def _update_async(
        self, pk: Any, data: dict[str, Any], request: Request
    ) -> Any:
        stmt = self.model_view._stmt_by_identifier(pk)

        for relation in self.model_view._form_relations:
            stmt = stmt.options(selectinload(relation))

        async with self.model_view.session_maker(
            expire_on_commit=False
        ) as session:  # type: AsyncSession
            result = await session.execute(stmt)
            obj = result.scalars().first()

            # 1) ВСЕ шаги и поля плана формируем здесь
            await self.model_view.on_model_change(data, obj, False, request)

            # 2) steps убираем ТОЛЬКО из data для _set_attributes_async,
            #    чтобы он не пытался обработать их как список ID
            clean_data = dict(data)
            clean_data.pop("steps", None)

            obj = await self._set_attributes_async(session, obj, clean_data)

            # 3) один commit сохраняет и DailyPlan, и его steps
            await session.commit()

            await self.model_view.after_model_change(data, obj, False, request)
            return obj

    async def _insert_async(self, data: dict[str, Any], request: Request) -> Any:
        obj = self.model_view.model()

        async with self.model_view.session_maker(expire_on_commit=False) as session:
            # 1) сначала даём модельному вью обработать ВСЕ данные (включая steps)
            #    здесь ты можешь создать связанные DailyPlanStep и т.д.
            await self.model_view.on_model_change(data, obj, True, request)

            # 2) убираем steps из data для установки простых атрибутов,
            #    чтобы _set_attributes_async не пытался пихать dict/list в Integer/ForeignKey
            clean_data = dict(data)
            clean_data.pop("steps", None)

            obj = await self._set_attributes_async(session, obj, clean_data)

            session.add(obj)
            await session.commit()

            await self.model_view.after_model_change(data, obj, True, request)
            return obj


class DailyPlanAdmin(
    CustomModelView[DailyPlan],
    model=DailyPlan,
):
    repo_type = DailyPlanRepository
    name_plural = "Планы на день"
    name = "План на день"
    category_icon = "fa-solid fa-diagram-project"
    category = "Планирование"

    list_template = "sqladmin/daily_plan_calendar.html"
    edit_template = "sqladmin/daily_plan_edit.html"
    create_template = "sqladmin/daily_plan_edit.html"

    form = DailyPlanForm

    column_list = (
        "date",
        "employee",
    )

    column_details_list = (
        "date",
        "employee",
        "steps",
    )

    column_labels = {
        "date": "Дата",
        "employee": "Сотрудник",
        "steps": "Этапы",
    }

    form_columns = [
        "date",
        "employee",
        "steps",
    ]

    form_rules = [
        "date",
        "employee",
    ]

    can_export = False
    can_create = True

    column_filters = [EmployeeFilter()]

    async def insert_model(self, request: Request, data: dict) -> Any:
        return await DailyPlanQuery(self).insert(data, request)

    async def update_model(self, request: Request, pk: str, data: dict) -> Any:
        return await DailyPlanQuery(self).update(pk, data, request)

    async def on_model_change(self, data, model, is_created, request):
        model.employee_id = data["employee_id"]
        model.date = data["date"]

        model.steps.clear()
        for step_data in data.get("steps", []):
            if not isinstance(step_data, dict):
                continue
            step_def_id = step_data.get("step_definition_id")
            if not step_def_id:
                continue
            planned = step_data.get("planned_quantity") or 0
            actual = step_data.get("actual_quantity") or 0

            model.steps.append(
                DailyPlanStep(
                    step_definition_id=step_def_id,
                    planned_quantity=int(planned),
                    actual_quantity=int(actual),
                )
            )

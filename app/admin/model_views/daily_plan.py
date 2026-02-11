from typing import Any

from fastapi import HTTPException
from sqladmin._queries import Query
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from starlette.requests import Request
from wtforms import (
    Form,
    SelectField,
    IntegerField,
    DateField,
    FieldList,
    FormField,
    HiddenField,
)
from wtforms.validators import DataRequired, NumberRange, Optional

from app.admin.custom_model_view import CustomModelView
from app.admin.filters.daily_plan import EmployeeFilter
from app.admin.save_result import SaveResult
from app.database import DailyPlan
from app.database.crud.daily_plans import DailyPlanRepository
from app.database.models import DailyPlanStep
from datetime import datetime, date as date_cls


class DailyPlanStepForm(Form):
    process_id = SelectField("Процесс", coerce=int, validators=[DataRequired()])
    step_definition_id = SelectField("Этап", coerce=int, validators=[DataRequired()])
    planned_quantity = IntegerField(
        "План, шт.", validators=[DataRequired(), NumberRange(min=0)]
    )


class DailyPlanForm(Form):
    employee_id = SelectField("Сотрудник", coerce=int, validators=[DataRequired()])
    date = DateField("Дата", validators=[DataRequired()])

    confirm_overwrite = HiddenField(default="0")

    steps = FieldList(FormField(DailyPlanStepForm), min_entries=0)


class DailyPlanQuery(Query):
    async def save(
        self,
        request: Request,
        data: dict[str, Any],
        pk: Any | None = None,
    ) -> SaveResult:
        async with self.model_view.session_maker(expire_on_commit=False) as session:
            # --- UPDATE (редактирование по pk) ---
            if pk is not None:
                stmt = self.model_view._stmt_by_identifier(pk)

                for relation in self.model_view._form_relations:
                    stmt = stmt.options(selectinload(relation))

                res = await session.execute(stmt)
                obj = res.scalars().first()
                if not obj:
                    raise HTTPException(status_code=404)

                # проверка на конфликт по employee_id + date
                employee_id = data.get("employee_id")
                plan_date = data.get("date")

                if employee_id and plan_date:
                    conflict_stmt = select(DailyPlan).where(
                        DailyPlan.employee_id == employee_id,
                        DailyPlan.date == plan_date,
                        DailyPlan.id != obj.id,  # не считаем сам объект
                    )
                    conflict_res = await session.execute(conflict_stmt)
                    conflict = conflict_res.scalars().first()
                    if conflict:
                        # просто возвращаем сигнал need_confirm
                        return SaveResult(obj=conflict, need_confirm=True)

                await self.model_view.on_model_change(data, obj, False, request)
                await session.commit()
                await self.model_view.after_model_change(data, obj, False, request)

                return SaveResult(obj=obj)

            # --- CREATE: проверка, что план не дублирует существующий ---
            employee_id = data.get("employee_id")
            plan_date = data.get("date")

            existing = None
            if employee_id and plan_date:
                stmt = select(DailyPlan).where(
                    DailyPlan.employee_id == employee_id,
                    DailyPlan.date == plan_date,
                )
                res = await session.execute(stmt)
                existing = res.scalars().first()

            if existing:
                return SaveResult(obj=existing, need_confirm=True)

            obj = DailyPlan()
            await self.model_view.on_model_change(data, obj, True, request)
            session.add(obj)
            await session.commit()
            await self.model_view.after_model_change(data, obj, True, request)

            return SaveResult(obj=obj)


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

    def list_query(self, request: Request):
        query = select(DailyPlan)

        # фильтр по сотруднику
        employee_id = request.query_params.get("employee_id")
        if employee_id:
            try:
                query = query.where(DailyPlan.employee_id == int(employee_id))
            except ValueError:
                pass

        # фильтр по дате из query-параметра
        date_str = request.query_params.get("date")
        if date_str:
            try:
                d: date_cls = datetime.strptime(date_str, "%Y-%m-%d").date()
                query = query.where(DailyPlan.date == d)
            except ValueError:
                pass

        return query

    async def insert_model(self, request: Request, data: dict) -> SaveResult:
        return await DailyPlanQuery(self).save(request, data, pk=None)

    async def update_model(self, request: Request, pk: str, data: dict) -> SaveResult:
        return await DailyPlanQuery(self).save(request, data, pk=pk)

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

            model.steps.append(
                DailyPlanStep(
                    step_definition_id=step_def_id,
                    planned_quantity=int(planned),
                )
            )

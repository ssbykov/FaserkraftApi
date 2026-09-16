from collections import defaultdict
from datetime import date
from datetime import date as date_type
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from starlette import status

from app.api.api_v1.dependencies import get_current_employee, require_admin_or_master
from app.api.services.norm_calculation import (
    build_norm_intervals,
    calculate_amount_for_step,
)
from app.core import settings
from app.database.crud.daily_plans import DailyPlanRepository, get_daily_plan_repo
from app.database.crud.employee_norm_calculations import (
    get_employee_norm_calculation_repo,
    EmployeeNormCalculationRepository,
)
from app.database.crud.processes import ProcessRepository, get_process_repo
from app.database.crud.products import ProductRepository, get_product_repo
from app.database.models.employee import Role
from app.database.models.product import ProductStatus
from app.database.schemas.employee import EmployeeRead
from app.database.schemas.product import (
    ProductRead,
    ProductCreate,
    ProductsCountByLastStepRead,
    ProductShortRead,
)
from app.database.schemas.statistics import (
    PeriodStatisticsRead,
    StepCountStatRead,
    ProcessCountStatRead,
    EmployeePlanStatRead,
    EmployeeEarningsRead,
)
from app.database.schemas.daily_plan_step import DailyPlanStepRead

router = APIRouter(
    tags=["Products"],
    prefix=settings.api.v1.products,
)


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_in: ProductCreate,
    repo: Annotated[ProductRepository, Depends(get_product_repo)],
    process_repo: Annotated[ProcessRepository, Depends(get_process_repo)],
    day_plan_repo: Annotated[DailyPlanRepository, Depends(get_daily_plan_repo)],
    employee: Annotated[EmployeeRead, Depends(get_current_employee)],
) -> ProductRead:
    try:
        first_step = await process_repo.get_first_step(product_in.process_id)

        if employee.role not in [
            Role.admin,
            Role.master,
        ] and not await day_plan_repo.check_step_def_in_daily_plan(
            date=date.today(),
            employee_id=employee.id,
            step_def_id=first_step.id,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="В планах нет этого этапа"
            )

        product = await repo.create_product(product_in)
        return ProductRead.model_validate(product)

    except IntegrityError as e:
        msg = str(e.orig)
        if (
            "violates foreign key constraint" in msg
            or "ForeignKeyViolationError" in msg
            or "foreign key" in msg.lower()
        ):
            raise HTTPException(
                status_code=422, detail="Указан несуществующий process_id"
            )
        if (
            "duplicate key value" in msg
            or "уже существует" in msg
            or "unique constraint" in msg.lower()
        ):
            raise HTTPException(
                status_code=409,
                detail="Продукт с таким серийным номером уже существует",
            )
        raise HTTPException(
            status_code=400, detail="Ошибка целостности данных при создании продукта"
        )

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка при создании продукта",
        )


@router.get(
    "/by-serial/{serial_number}",
    response_model=ProductRead,
    status_code=status.HTTP_200_OK,
)
async def get_product(
    serial_number: str,
    repo: Annotated[ProductRepository, Depends(get_product_repo)],
    employee: Annotated[EmployeeRead, Depends(get_current_employee)],
) -> ProductRead:
    try:
        product = await repo.get(serial_number=serial_number)
        return ProductRead.model_validate(product)
    except HTTPException as exc:
        raise exc
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка при получении продукта",
        )


@router.get(
    "/stats/by-last-done-step",
    response_model=list[ProductsCountByLastStepRead],
    status_code=status.HTTP_200_OK,
)
async def get_products_stats_by_last_done_step(
    repo: Annotated[ProductRepository, Depends(get_product_repo)],
    employee: Annotated[EmployeeRead, Depends(get_current_employee)],
) -> list[ProductsCountByLastStepRead]:
    try:
        data = await repo.get_counts_by_last_done_step()
        return [ProductsCountByLastStepRead(**item) for item in data]
    except HTTPException as exc:
        raise exc
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка при получении статистики по продуктам",
        )


@router.get(
    "/finished",
    response_model=list[ProductShortRead],
    status_code=status.HTTP_200_OK,
)
async def get_finished_products(
    repo: Annotated[ProductRepository, Depends(get_product_repo)],
    employee: Annotated[EmployeeRead, Depends(get_current_employee)],
) -> list[ProductShortRead]:
    try:
        employee_id = None
        if employee.role not in [Role.admin, Role.master]:
            employee_id = employee.id

        products = await repo.get_finished_products(employee_id=employee_id)
        return [ProductShortRead.model_validate(p) for p in products]
    except HTTPException as exc:
        raise exc
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка при получении списка завершённых продуктов",
        )


async def _calculate_period_earnings(
    *,
    repo: ProductRepository,
    daily_plan_repo: DailyPlanRepository,
    norm_calc_repo: EmployeeNormCalculationRepository,
    date_from: date_type,
    date_to: date_type,
    employee_id: int | None,
) -> tuple[list[dict], dict[int, Decimal]]:
    """
    Считает выработку в рублях за весь запрошенный период (месяц, квартал,
    год или произвольный диапазон). Отображаемый диапазон совпадает с
    полным периодом действия нормы, поэтому доля рабочих дней равна 1 и
    формула calculate_amount_for_step сводится к обычной сумме за период.
    """
    steps_data = await repo.get_completed_steps_stats_by_period(
        date_from=date_from,
        date_to=date_to,
        employee_id=employee_id,
    )

    daily_rows = await repo.get_completed_steps_by_day(
        date_from=date_from,
        date_to=date_to,
        employee_id=employee_id,
    )
    working_days_map = await daily_plan_repo.get_working_days_by_employee(
        date_from=date_from,
        date_to=date_to,
        employee_id=employee_id,
    )

    step_definition_ids = {row["step_definition_id"] for row in daily_rows}
    norms_by_step = await norm_calc_repo.get_norms_for_steps(step_definition_ids)

    daily_counts_map: dict[tuple[int, int], dict[date_type, int]] = defaultdict(dict)
    for row in daily_rows:
        key = (row["employee_id"], row["step_definition_id"])
        daily_counts_map[key][row["day"]] = row["count"]

    employee_step_amounts: dict[tuple[int, int], Decimal] = {}
    for key, daily_counts in daily_counts_map.items():
        emp_id, step_def_id = key
        norms = norms_by_step.get(step_def_id, [])
        intervals = build_norm_intervals(norms, date_from, date_to)
        employee_working_days = working_days_map.get(emp_id, set())

        # Отображаемый диапазон == полный период, поэтому period_working_days
        # передаём тем же множеством: доля рабочих дней будет равна 1.
        amount = calculate_amount_for_step(
            intervals=intervals,
            daily_counts=daily_counts,
            employee_working_days=employee_working_days,
            period_working_days=employee_working_days,
        )
        employee_step_amounts[key] = amount

    for item in steps_data:
        key = (item["employee_id"], item["step_definition_id"])
        item["total_amount"] = employee_step_amounts.get(key, Decimal("0"))

    amounts_by_employee: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
    for (emp_id, _), amount in employee_step_amounts.items():
        amounts_by_employee[emp_id] += amount

    return steps_data, amounts_by_employee


async def _calculate_first_half_earnings(
    *,
    repo: ProductRepository,
    daily_plan_repo: DailyPlanRepository,
    norm_calc_repo: EmployeeNormCalculationRepository,
    month_from: date_type,
    month_to: date_type,
    first_half_to: date_type,
    employee_id: int | None,
) -> tuple[list[dict], dict[int, Decimal]]:
    """
    Считает аванс за 1-15 число как долю от месячной нормы, взвешенную по
    фактической выработке в первой половине месяца.

    Ключевое отличие от _calculate_period_earnings: интервалы нормы и
    working_days_map строятся на границах ВСЕГО месяца (month_from,
    month_to), а не обрезаются по first_half_to. Иначе знаменатель доли
    ("рабочих дней в месяце") не увидит дни после 15 числа, и расчёт
    аванса перестанет быть аддитивным относительно суммы за весь месяц.
    """
    steps_data = await repo.get_completed_steps_stats_by_period(
        date_from=month_from,
        date_to=first_half_to,
        employee_id=employee_id,
    )

    daily_rows = await repo.get_completed_steps_by_day(
        date_from=month_from,
        date_to=first_half_to,
        employee_id=employee_id,
    )

    # Рабочие дни нужны за ВЕСЬ месяц - это знаменатель доли.
    full_month_working_days_map = await daily_plan_repo.get_working_days_by_employee(
        date_from=month_from,
        date_to=month_to,
        employee_id=employee_id,
    )

    step_definition_ids = {row["step_definition_id"] for row in daily_rows}
    norms_by_step = await norm_calc_repo.get_norms_for_steps(step_definition_ids)

    daily_counts_map: dict[tuple[int, int], dict[date_type, int]] = defaultdict(dict)
    for row in daily_rows:
        key = (row["employee_id"], row["step_definition_id"])
        daily_counts_map[key][row["day"]] = row["count"]

    employee_step_amounts: dict[tuple[int, int], Decimal] = {}
    for key, daily_counts in daily_counts_map.items():
        emp_id, step_def_id = key
        norms = norms_by_step.get(step_def_id, [])

        # Интервалы строим на всём месяце, иначе последний интервал
        # обрежется по first_half_to и знаменатель окажется неверным.
        intervals = build_norm_intervals(norms, month_from, month_to)

        full_month_days = full_month_working_days_map.get(emp_id, set())
        first_half_days = {d for d in full_month_days if d <= first_half_to}

        amount = calculate_amount_for_step(
            intervals=intervals,
            daily_counts=daily_counts,
            employee_working_days=first_half_days,
            period_working_days=full_month_days,
        )
        employee_step_amounts[key] = amount

    for item in steps_data:
        key = (item["employee_id"], item["step_definition_id"])
        item["total_amount"] = employee_step_amounts.get(key, Decimal("0"))

    amounts_by_employee: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
    for (emp_id, _), amount in employee_step_amounts.items():
        amounts_by_employee[emp_id] += amount

    return steps_data, amounts_by_employee


def _build_employee_earnings(
    *,
    employee_plans_data: list[dict],
    steps_data: list[dict],
    amounts_by_employee: dict[int, Decimal],
) -> list[EmployeeEarningsRead]:
    """
    Собирает EmployeeEarningsRead из посчитанной выработки для набора
    сотрудников. Используется и для основного периода, и для аванса.
    """
    steps_by_employee: dict[int, list[dict]] = defaultdict(list)
    for s in steps_data:
        steps_by_employee[s["employee_id"]].append(s)

    return [
        EmployeeEarningsRead(
            employee_id=item["employee_id"],
            employee_name=item["employee_name"],
            total_earned=amounts_by_employee.get(
                item["employee_id"], Decimal("0")
            ).quantize(Decimal("0.01")),
            steps=[
                StepCountStatRead(**s)
                for s in steps_by_employee.get(item["employee_id"], [])
            ],
        )
        for item in employee_plans_data
    ]


@router.get(
    "/statistics/period",
    response_model=PeriodStatisticsRead,
    status_code=status.HTTP_200_OK,
)
async def get_period_statistics(
    date_from: date,
    date_to: date,
    repo: Annotated[ProductRepository, Depends(get_product_repo)],
    daily_plan_repo: Annotated[DailyPlanRepository, Depends(get_daily_plan_repo)],
    norm_calc_repo: Annotated[
        EmployeeNormCalculationRepository, Depends(get_employee_norm_calculation_repo)
    ],
    employee: Annotated[EmployeeRead, Depends(get_current_employee)],
    include_first_half: bool = False,
):
    try:
        employee_id = None
        finished_products_data = []

        if employee.role in [Role.admin, Role.master]:
            finished_products_data = await repo.get_finished_products_stats_by_period(
                date_from=date_from,
                date_to=date_to,
            )
        else:
            employee_id = employee.id

        total_working_days = await daily_plan_repo.get_working_days_count_by_period(
            date_from=date_from,
            date_to=date_to,
            employee_id=employee_id,
        )

        steps_data, amounts_by_employee = await _calculate_period_earnings(
            repo=repo,
            daily_plan_repo=daily_plan_repo,
            norm_calc_repo=norm_calc_repo,
            date_from=date_from,
            date_to=date_to,
            employee_id=employee_id,
        )

        employee_plans_data = await daily_plan_repo.get_employee_plan_stats_by_period(
            date_from=date_from,
            date_to=date_to,
            employee_id=employee_id,
        )

        employee_plans = [
            EmployeePlanStatRead(
                employee_id=item["employee_id"],
                employee_name=item["employee_name"],
                working_days=item["working_days"],
                steps=[DailyPlanStepRead.model_validate(s) for s in item["steps"]],
            )
            for item in employee_plans_data
        ]

        employee_earnings = _build_employee_earnings(
            employee_plans_data=employee_plans_data,
            steps_data=steps_data,
            amounts_by_employee=amounts_by_employee,
        )

        total_earned_all = sum(amounts_by_employee.values(), Decimal("0")).quantize(
            Decimal("0.01")
        )

        # --- Аванс: сумма выработки за 1-15 число месяца ---
        # Считается только по явному запросу клиента и только если период
        # действительно начинается с 1 числа месяца. Использует отдельную
        # функцию _calculate_first_half_earnings, которая строит интервалы
        # норм и working_days на границах ВСЕГО месяца, а не только 1-15,
        # чтобы аванс + остаток месяца всегда были равны сумме за весь месяц.
        first_half_earnings: list[EmployeeEarningsRead] = []

        if include_first_half and date_from.day == 1:
            first_half_to = min(date_from.replace(day=15), date_to)

            fh_steps_data, fh_amounts_by_employee = await _calculate_first_half_earnings(
                repo=repo,
                daily_plan_repo=daily_plan_repo,
                norm_calc_repo=norm_calc_repo,
                month_from=date_from,
                month_to=date_to,
                first_half_to=first_half_to,
                employee_id=employee_id,
            )

            first_half_earnings = _build_employee_earnings(
                employee_plans_data=employee_plans_data,
                steps_data=fh_steps_data,
                amounts_by_employee=fh_amounts_by_employee,
            )

        return PeriodStatisticsRead(
            total_working_days=total_working_days,
            finished_products=[
                ProcessCountStatRead(**item) for item in finished_products_data
            ],
            total_steps=[StepCountStatRead(**item) for item in steps_data],
            employee_plans=employee_plans,
            employee_earnings=employee_earnings,
            first_half_earnings=first_half_earnings,
            total_earned_all=total_earned_all,
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Произошла ошибка при получении статистики",
        )


@router.get(
    "/by-step-employee-day",
    response_model=list[ProductRead],
    status_code=status.HTTP_200_OK,
)
async def get_products_by_step_employee_day(
    step_definition_id: int,
    day: date_type,
    repo: Annotated[ProductRepository, Depends(get_product_repo)],
    employee: Annotated[EmployeeRead, Depends(get_current_employee)],
    employee_id: int | None = None,
) -> list[ProductRead]:
    try:
        if employee.role not in [Role.admin, Role.master]:
            effective_employee_id = employee.id
        else:
            effective_employee_id = employee_id or employee.id

        products = await repo.list_by_step_employee_and_day(
            step_definition_id=step_definition_id,
            employee_id=effective_employee_id,
            day=day,
        )
        return [ProductRead.model_validate(p) for p in products]

    except HTTPException as exc:
        raise exc
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка при получении продуктов по этапу/сотруднику/дате",
        )


@router.post(
    "/change_product_process",
    response_model=ProductRead,
    status_code=status.HTTP_200_OK,
)
async def change_product_process(
    product_id: int,
    new_process_id: int,
    repo: Annotated[ProductRepository, Depends(get_product_repo)],
    employee: Annotated[EmployeeRead, Depends(require_admin_or_master)],
) -> ProductRead:
    try:
        product = await repo.change_product_process(
            product_id=product_id, new_process_id=new_process_id
        )
        return ProductRead.model_validate(product)
    except HTTPException as exc:
        raise exc
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка при изменении процесса продукта",
        )


@router.post(
    "/{product_id}/change_status",
    response_model=ProductRead,
    status_code=status.HTTP_200_OK,
)
async def change_product_status(
    product_id: int,
    status: ProductStatus,
    repo: Annotated[ProductRepository, Depends(get_product_repo)],
    employee: Annotated[EmployeeRead, Depends(require_admin_or_master)],
) -> ProductRead:
    try:
        product = await repo.set_status(product_id=product_id, status=status)
        return ProductRead.model_validate(product)
    except HTTPException as exc:
        raise exc
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка при изменении статуса продукта",
        )


@router.get(
    "/by-last-completed-step",
    response_model=list[ProductRead],
    status_code=status.HTTP_200_OK,
)
async def get_products_by_last_completed_step(
    process_id: int,
    step_definition_id: int,
    repo: Annotated[ProductRepository, Depends(get_product_repo)],
    employee: Annotated[EmployeeRead, Depends(get_current_employee)],
) -> list[ProductRead]:
    try:
        products = await repo.list_by_process_and_last_completed_step(
            process_id=process_id,
            step_definition_id=step_definition_id,
        )
        return [ProductRead.model_validate(item) for item in products]
    except HTTPException as exc:
        raise exc
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла внутренняя ошибка при получении продуктов",
        )


@router.get(
    "/not-normal",
    response_model=list[ProductRead],
    status_code=status.HTTP_200_OK,
)
async def get_products_not_normal(
    repo: Annotated[ProductRepository, Depends(get_product_repo)],
    employee: Annotated[EmployeeRead, Depends(get_current_employee)],
) -> list[ProductRead]:
    try:
        products = await repo.get_products_not_normal()
        return [ProductRead.model_validate(p) for p in products]
    except HTTPException as exc:
        raise exc
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка при получении списка проблемных продуктов",
        )

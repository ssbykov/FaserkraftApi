from calendar import monthrange
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
from app.database.crud.production_calendar import (
    ProductionCalendarRepository,
    get_production_calendar_repo,
)
from app.database.crud.products import ProductRepository, get_product_repo
from app.database.models.employee import Role
from app.database.models.product import ProductStatus
from app.database.schemas.daily_plan_step import DailyPlanStepRead
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
    norm_calc_repo: EmployeeNormCalculationRepository,
    production_calendar_repo: ProductionCalendarRepository,
    date_from: date_type,
    date_to: date_type,
    employee_id: int | None,
) -> tuple[list[dict], dict[int, Decimal]]:
    """
    Считает выработку в рублях за запрошенный период (месяц, квартал, год
    или произвольный диапазон).

    Знаменатель формулы (working_days_in_month) - это количество рабочих
    дней по производственному календарю РФ за КАЖДЫЙ календарный месяц,
    покрываемый диапазоном [date_from, date_to]. Если диапазон охватывает
    несколько месяцев (квартал/год), каждый месяц считается со своим
    знаменателем, а результаты суммируются - иначе для кварталов/года
    потерялась бы аддитивность относительно помесячного аванса.
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

    step_definition_ids = {row["step_definition_id"] for row in daily_rows}
    norms_by_step = await norm_calc_repo.get_norms_for_steps(step_definition_ids)

    daily_counts_map: dict[tuple[int, int], dict[date_type, int]] = defaultdict(dict)
    for row in daily_rows:
        key = (row["employee_id"], row["step_definition_id"])
        daily_counts_map[key][row["day"]] = row["count"]

    # Разбиваем запрошенный диапазон на календарные месяцы, чтобы для
    # каждого месяца использовать его собственное количество рабочих дней.
    month_ranges = _split_into_calendar_months(date_from, date_to)

    working_days_by_month: dict[tuple[int, int], int] = {}
    for month_start, month_end in month_ranges:
        working_days_by_month[(month_start.year, month_start.month)] = (
            await production_calendar_repo.get_working_days_count(
                month_start, month_end
            )
        )

    employee_step_amounts: dict[tuple[int, int], Decimal] = {}
    for key, daily_counts in daily_counts_map.items():
        emp_id, step_def_id = key
        norms = norms_by_step.get(step_def_id, [])

        amount = Decimal("0")
        for month_start, month_end in month_ranges:
            intervals = build_norm_intervals(norms, month_start, month_end)
            working_days_in_month = working_days_by_month[
                (month_start.year, month_start.month)
            ]

            # daily_counts за пределами текущего месяца интервалам не
            # соответствуют - calculate_amount_for_step сам отфильтрует
            # по границам интервала, но intervals здесь уже обрезаны
            # по месяцу, поэтому лишние дни просто не совпадут ни с одним
            # интервалом и не будут учтены.
            amount += calculate_amount_for_step(
                intervals=intervals,
                daily_counts=daily_counts,
                working_days_in_month=working_days_in_month,
            )

        employee_step_amounts[key] = amount.quantize(Decimal("0.01"))

    for item in steps_data:
        key = (item["employee_id"], item["step_definition_id"])
        item["total_amount"] = employee_step_amounts.get(key, Decimal("0"))

    amounts_by_employee: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
    for (emp_id, _), amount in employee_step_amounts.items():
        amounts_by_employee[emp_id] += amount

    return steps_data, amounts_by_employee


def _split_into_calendar_months(
    date_from: date_type,
    date_to: date_type,
) -> list[tuple[date_type, date_type]]:
    """
    Разбивает диапазон [date_from, date_to] на список интервалов,
    каждый из которых целиком лежит в одном календарном месяце.

    Например, для 15 сентября - 20 октября вернёт:
        [(15 сентября, 30 сентября), (1 октября, 20 октября)]
    """
    ranges: list[tuple[date_type, date_type]] = []
    current_start = date_from

    while current_start <= date_to:
        last_day_of_month = monthrange(current_start.year, current_start.month)[1]
        month_end = current_start.replace(day=last_day_of_month)
        current_end = min(month_end, date_to)

        ranges.append((current_start, current_end))

        if current_end >= date_to:
            break

        current_start = current_end + date_type.resolution

    return ranges


async def _calculate_first_half_earnings(
    *,
    repo: ProductRepository,
    norm_calc_repo: EmployeeNormCalculationRepository,
    production_calendar_repo: ProductionCalendarRepository,
    month_from: date_type,
    month_to: date_type,
    first_half_to: date_type,
    employee_id: int | None,
) -> tuple[list[dict], dict[int, Decimal]]:
    """
    Считает аванс за 1-15 число как долю от месячной нормы.

    Знаменатель (working_days_in_month) берётся за ВЕСЬ календарный
    месяц (month_from..month_to) через ProductionCalendarRepository -
    тем же способом, что и в _calculate_period_earnings для полного
    периода. Числитель - фактическая выработка только за 1-15 число,
    так как daily_rows запрашиваются с date_to=first_half_to.

    Благодаря общему (полномесячному) знаменателю сумма аванса (1-15)
    и сумма за оставшуюся часть месяца (16-конец) в точности
    складываются в сумму за весь месяц.
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

    step_definition_ids = {row["step_definition_id"] for row in daily_rows}
    norms_by_step = await norm_calc_repo.get_norms_for_steps(step_definition_ids)

    daily_counts_map: dict[tuple[int, int], dict[date_type, int]] = defaultdict(dict)
    for row in daily_rows:
        key = (row["employee_id"], row["step_definition_id"])
        daily_counts_map[key][row["day"]] = row["count"]

    working_days_in_month = await production_calendar_repo.get_working_days_count(
        month_from, month_to
    )

    employee_step_amounts: dict[tuple[int, int], Decimal] = {}
    for key, daily_counts in daily_counts_map.items():
        emp_id, step_def_id = key
        norms = norms_by_step.get(step_def_id, [])

        intervals = build_norm_intervals(norms, month_from, month_to)

        amount = calculate_amount_for_step(
            intervals=intervals,
            daily_counts=daily_counts,
            working_days_in_month=working_days_in_month,
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
    production_calendar_repo: Annotated[
        ProductionCalendarRepository, Depends(get_production_calendar_repo)
    ],
    employee: Annotated[EmployeeRead, Depends(get_current_employee)],
    include_first_half: bool = False,
):
    try:
        if date_from > date_to:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="date_from не может быть позже date_to",
            )

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
            norm_calc_repo=norm_calc_repo,
            production_calendar_repo=production_calendar_repo,
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
        # действительно начинается с 1 числа месяца.
        #
        # working_days_in_month для аванса берётся за ВЕСЬ месяц через
        # production_calendar_repo - тот же знаменатель, что и для полного
        # периода, поэтому сумма аванса + сумма за 16-конец месяца равны
        # сумме за весь месяц (аддитивность гарантируется тем, что
        # знаменатель не зависит от подпериода, а только от месяца).
        first_half_earnings: list[EmployeeEarningsRead] = []

        if include_first_half and date_from.day == 1:
            first_half_to = min(date_from.replace(day=15), date_to)
            last_day_of_month = monthrange(date_from.year, date_from.month)[1]
            month_to = date_from.replace(day=last_day_of_month)

            fh_steps_data, fh_amounts_by_employee = (
                await _calculate_first_half_earnings(
                    repo=repo,
                    norm_calc_repo=norm_calc_repo,
                    production_calendar_repo=production_calendar_repo,
                    month_from=date_from,
                    month_to=month_to,
                    first_half_to=first_half_to,
                    employee_id=employee_id,
                )
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

from datetime import date as date_type, timedelta
from decimal import Decimal

from app.database import EmployeeNormCalculation


def build_norm_intervals(
    norms: list[EmployeeNormCalculation],
    date_from: date_type,
    date_to: date_type,
) -> list[tuple[date_type, date_type, Decimal]]:
    """
    Строит список интервалов (start, end, calculated_norm), обрезанных
    по границам [date_from, date_to]. Каждый интервал — период действия
    одной конкретной записи нормы (до появления следующей по дате).
    """
    relevant = [n for n in norms if n.date <= date_to]
    if not relevant:
        return []

    intervals = []
    for i, norm in enumerate(relevant):
        start = norm.date
        end = (
            relevant[i + 1].date - timedelta(days=1)
            if i + 1 < len(relevant)
            else date_to
        )

        clipped_start = max(start, date_from)
        clipped_end = min(end, date_to)

        if clipped_start > clipped_end:
            continue

        norm_value = norm.calculated_norm
        if norm_value is None:
            continue

        intervals.append((clipped_start, clipped_end, norm_value))

    return intervals


def calculate_amount_for_step(
    intervals: list[tuple[date_type, date_type, Decimal]],
    daily_counts: dict[date_type, int],
    employee_working_days: set[date_type],
    period_working_days: set[date_type],
) -> Decimal:
    """
    Для каждого интервала действия нормы считает сумму как:

        norm_value
        x (рабочих дней сотрудника в отображаемом периоде / рабочих дней
           сотрудника за весь период действия нормы)
        x (среднедневная выработка за отображаемый период)

    где "отображаемый период" — фактический диапазон, за который считается
    сумма (например, 1-15 число для аванса или весь месяц для обычного
    расчёта), а "весь период действия нормы" передаётся отдельно через
    period_working_days и НЕ обрезается по отображаемому диапазону.

    Математически первый множитель (рабочих дней в периоде) сокращается
    со знаменателем среднедневной выработки, поэтому итоговая формула
    эквивалентна:

        norm_value x count_за_период / рабочих_дней_за_весь_период

    Это гарантирует аддитивность: сумма за подпериод (например, аванс за
    1-15 число) плюс сумма за оставшуюся часть периода всегда равна сумме
    за весь период целиком — независимо от того, насколько неравномерно
    распределена фактическая выработка внутри периода.

    employee_working_days — рабочие дни сотрудника, попадающие именно в
    отображаемый диапазон (например, только с 1 по 15 число).
    period_working_days — ВСЕ рабочие дни сотрудника за полный период
    действия нормы (обычно весь месяц). Для обычного (немесячного среза)
    расчёта, где отображаемый диапазон совпадает с полным периодом,
    передайте employee_working_days и period_working_days одинаковыми —
    тогда доля будет равна 1 и формула не изменит поведение.

    Если норм для шага нет вообще (intervals пуст) — возвращает 0.
    """
    total = Decimal("0")

    for start, end, norm_value in intervals:
        working_days_in_period = {
            d for d in employee_working_days if start <= d <= end
        }
        if not working_days_in_period:
            continue

        working_days_in_full_period = {
            d for d in period_working_days if start <= d <= end
        }
        if not working_days_in_full_period:
            continue

        count_in_period = sum(
            count
            for day, count in daily_counts.items()
            if start <= day <= end
        )

        days_share = Decimal(len(working_days_in_period)) / len(
            working_days_in_full_period
        )
        avg_per_working_day = Decimal(count_in_period) / len(
            working_days_in_period
        )

        total += norm_value * days_share * avg_per_working_day

    return total.quantize(Decimal("0.01"))

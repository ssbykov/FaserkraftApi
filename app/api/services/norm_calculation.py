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
) -> Decimal:
    """
    Для каждого интервала действия нормы считает среднее количество
    закрытых шагов на один рабочий день сотрудника и умножает на
    calculated_norm этого интервала. Результат округляется до копеек.

    Если норм для шага нет вообще (intervals пуст) — возвращает 0.
    """
    total = Decimal("0")

    for start, end, norm_value in intervals:
        working_days_in_interval = {
            d for d in employee_working_days if start <= d <= end
        }
        if not working_days_in_interval:
            continue

        total_count_in_interval = sum(
            count for day, count in daily_counts.items() if start <= day <= end
        )
        avg_per_working_day = Decimal(total_count_in_interval) / len(
            working_days_in_interval
        )
        total += avg_per_working_day * norm_value

    return total.quantize(Decimal("0.01"))
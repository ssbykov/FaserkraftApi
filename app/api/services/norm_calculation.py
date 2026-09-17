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
    working_days_in_month: int,
) -> Decimal:
    """
    Для каждого интервала действия нормы считает сумму как:

        norm_value x count_за_интервал / working_days_in_month

    где:
    - count_за_интервал - фактическое количество закрытых шагов за
      интервал (не зависит от того, есть ли daily_plan на день - просто
      сумма реально выполненных операций);
    - working_days_in_month - общее количество рабочих дней за весь
      период действия нормы (обычно календарный месяц), взятое из
      производственного календаря РФ. Одно и то же число для ВСЕХ
      сотрудников и для ЛЮБОГО подпериода этого месяца (например, для
      аванса за 1-15 число используется тот же знаменатель, что и для
      расчёта за весь месяц).

    Экономический смысл: norm_value уже выражает "оклад за одну операцию
    при выполнении дневной нормы", поэтому норма выработки уже учитывает
    количество рабочих дней в периоде на этапе своего расчёта
    (norm_value = оклад x коэффициент / дневная_норма). Деление здесь на
    working_days_in_month распределяет причитающийся оклад
    пропорционально фактически произведённому объёму работы относительно
    того, сколько сотрудник должен был произвести за весь месяц.

    Такой знаменатель гарантирует две вещи одновременно:
    1. Аддитивность: сумма за подпериод (аванс за 1-15) плюс сумма за
       оставшуюся часть месяца всегда равна сумме за весь месяц,
       независимо от того, насколько неравномерно распределена
       фактическая выработка внутри месяца.
    2. Корректный учёт отпуска/больничного: если сотрудник объективно
       отработал меньше дней с той же результативностью, он получает
       пропорционально меньшую долю оклада - без искусственного
       завышения или занижения относительно других сотрудников.

    working_days_in_month берётся из производственного календаря РФ, а
    не из daily_plan сотрудника, потому что daily_plan создаётся только
    по факту наступления дня и не покрывает будущие дни ещё не
    завершившегося месяца - использование daily_plan как знаменателя для
    текущего месяца исказило бы долю в пользу уже прошедшей части месяца.

    Если норм для шага нет вообще (intervals пуст) или
    working_days_in_month <= 0 - возвращает 0.
    """
    total = Decimal("0")

    if working_days_in_month <= 0:
        return total

    for start, end, norm_value in intervals:
        count_in_interval = sum(
            count for day, count in daily_counts.items() if start <= day <= end
        )
        if count_in_interval == 0:
            continue

        total += norm_value * Decimal(count_in_interval) / working_days_in_month

    return total.quantize(Decimal("0.01"))

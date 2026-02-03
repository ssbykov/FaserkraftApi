from dataclasses import dataclass
from typing import Optional

from app.database import DailyPlan


@dataclass
class SaveResult:
    obj: Optional[DailyPlan]
    need_confirm: bool = False

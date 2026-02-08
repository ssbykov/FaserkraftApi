from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import Employee, SessionDep
from app.database.crud.mixines import GetBackNextIdMixin
from app.database.models import Device, User


def get_employee_repo(session: SessionDep) -> "EmployeeRepository":
    return EmployeeRepository(session)


class EmployeeRepository(GetBackNextIdMixin[Employee]):
    model = Employee

    async def attach_device(self, user_id: int, device: Device) -> Employee:
        # 1. сотрудник по user_id
        stmt = (
            select(self.model)
            .options(selectinload(self.model.user))
            .where(self.model.user_id == user_id)
        )
        employee = await self.session.scalar(stmt)
        if employee is None:
            raise HTTPException(
                status_code=404,
                detail="Сотрудник для этого пользователя не найден",
            )

        # 2. отвязать этот девайс от другого сотрудника (если уже занят)
        stmt_other = select(self.model).where(self.model.device_id == device.id)
        other_employee = await self.session.scalar(stmt_other)
        if other_employee and other_employee.id != employee.id:
            other_employee.device_id = None

        # 3. привязать девайс к текущему сотруднику
        employee.device_id = device.id

        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

        await self.session.refresh(employee)
        return employee

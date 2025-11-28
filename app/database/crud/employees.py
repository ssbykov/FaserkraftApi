from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import Employee, SessionDep
from app.database.crud.mixines import GetBackNextIdMixin
from app.database.models import Device


def get_employee_repo(session: SessionDep) -> "EmployeeRepository":
    return EmployeeRepository(session)


class EmployeeRepository(GetBackNextIdMixin[Employee]):
    model = Employee

    async def attach_device(self, user_id: int, device: Device) -> Employee:
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

        employee.device_id = device.id

        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

        await self.session.refresh(employee)
        return employee

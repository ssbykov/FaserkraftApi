from app.database import Employee
from app.database.crud.mixines import GetBackNextIdMixin


class EmployeeRepository(GetBackNextIdMixin[Employee]):
    model = Employee
